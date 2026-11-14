"""Portable launcher: prefer this PC's licensed MATLAB, otherwise use Python."""
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'matlab-engine'))
sys.path.insert(0, str(ROOT))
from matlab_host import MatlabSetupError, prepare_engine, select_backend
from scripts.discovery import LanAdvertisement


def scoring_certificate(folder):
    """Separate development CA; never replace the app's existing certificate."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    folder.mkdir(parents=True, exist_ok=True)
    cert, keyfile = folder / 'server.pem', folder / 'server-key.pem'
    if cert.exists() and keyfile.exists():
        existing = x509.load_pem_x509_certificate(cert.read_bytes())
        if existing.not_valid_after_utc > datetime.now(timezone.utc) + timedelta(days=1):
            return cert, keyfile
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'THE VAULT host scorer')])
    value = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
             .serial_number(x509.random_serial_number())
             .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=5))
             .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
             .add_extension(x509.SubjectAlternativeName([x509.DNSName('host.docker.internal'),
                 x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
             .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
             .sign(key, hashes.SHA256()))
    with os.fdopen(os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'wb') as handle:
        handle.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    cert.write_bytes(value.public_bytes(serialization.Encoding.PEM))
    return cert, keyfile


def compose_command(host_matlab=False):
    command = ['docker', 'compose', '-f', 'docker-compose.yml']
    if host_matlab:
        command += ['-f', 'compose.matlab-dev.yml']
    return command


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def start_scoring(backend, port, bind, startup_timeout):
    import uvicorn
    import service
    # Do not overwrite scorer certificates while another service owns this port.
    with socket.socket() as probe:
        try:
            probe.bind((bind, port))
        except OSError as exc:
            raise MatlabSetupError(f'Host scoring port {port} is already in use. Stop the previous local launcher.') from exc
    cert, key = scoring_certificate(ROOT / '.local/scoring-certs')
    service.MODE = backend
    server = uvicorn.Server(uvicorn.Config(service.app, host=bind, port=port, access_log=False,
        ssl_keyfile=str(key), ssl_certfile=str(cert)))
    worker = threading.Thread(target=server.run, name='vault-scoring', daemon=True)
    worker.start()
    deadline = time.monotonic() + startup_timeout
    try:
        while not server.started:
            if not worker.is_alive():
                raise MatlabSetupError('The scoring service failed its startup checks; see the error above. No fallback was substituted.')
            if time.monotonic() >= deadline:
                raise MatlabSetupError('MATLAB startup timed out. Open desktop MATLAB and finish any activation dialog, then retry.')
            time.sleep(0.25)
    except BaseException:
        server.should_exit = True
        worker.join(timeout=5)
        raise
    return server, worker, cert


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['auto', 'matlab-engine', 'python-reference'], default='auto')
    parser.add_argument('--matlab-root', help='Override discovery for a nonstandard installation')
    parser.add_argument('--check', action='store_true', help='Report discovery only; no installation, license checkout, or services')
    parser.add_argument('--local', action='store_true', help='Run all services locally instead of using Docker infrastructure')
    parser.add_argument('--no-build', action='store_true', help='Reuse Docker images already built from the current source')
    parser.add_argument('--port', type=int, default=8443, help='Gateway port in --local mode')
    parser.add_argument('--startup-timeout', type=int, default=180)
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    backend, installation = select_backend(args.backend, args.matlab_root)
    if args.check:
        print(json.dumps({'backend': backend, 'matlab_root': str(installation.root) if installation else None,
            'release': installation.release if installation else None, 'license_checked': False,
            'compiler_sdk_required': False,
            'detail': 'License and toolboxes are checked when MATLAB starts.' if installation else
                      'No complete desktop MATLAB installation detected; the Python reference is available.'}, indent=2))
        return 0
    if installation and os.getenv('VAULT_ENGINE_PREPARED') != str(installation.root):
        env = prepare_engine(installation, ROOT)
        env['VAULT_ENGINE_PREPARED'] = str(installation.root)
        # A new interpreter is required for Linux/macOS dynamic-loader paths.
        return subprocess.call([sys.executable, str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)], env=env)
    print(f'THE VAULT scoring: {backend}', flush=True)
    if not installation:
        print('Using the explicitly identified Python reference; MATLAB is not active.', flush=True)
    run([sys.executable, 'scripts/bootstrap.py'])
    build = [] if args.no_build else ['--build']
    if backend == 'python-reference' and not args.local:
        run(compose_command() + ['up', '-d', *build])
        advertisement = LanAdvertisement(ROOT)
        try:
            print('Keep this terminal open for automatic phone discovery.', flush=True)
            while True:
                advertisement.refresh()
                time.sleep(5)
        finally:
            advertisement.close()

    os.environ['SCORING_BACKEND'] = backend
    os.environ['SCORING_TOKEN'] = secrets.token_urlsafe(32)
    os.environ['PYTHONPATH'] = os.pathsep.join(filter(None, [str(ROOT), str(ROOT / 'vision-py'),
        str(ROOT / 'matlab-engine'), os.getenv('PYTHONPATH', '')]))
    print('Checking the scorer before starting the gateway...', flush=True)
    server, worker, cert = start_scoring(backend, 9910, '127.0.0.1' if args.local else '0.0.0.0', args.startup_timeout)
    children = []
    advertisement = LanAdvertisement(ROOT, args.port if args.local else 8443)
    try:
        if args.local:
            os.environ['SCORING_URL'] = 'https://127.0.0.1:9910'
            os.environ['SCORING_CA_FILE'] = str(cert)
            # Local mode always uses the local transports rather than stale Docker URLs.
            os.environ['DATABASE_URL'] = 'sqlite:///.local/vault.db'
            os.environ['REDIS_URL'] = ''
            os.environ['S3_ENDPOINT'] = ''
            os.environ['VISION_ADDRESS'] = '127.0.0.1:50051'
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            for command in ([sys.executable, '-m', 'src.server'],
                [sys.executable, '-m', 'uvicorn', 'gateway.app.main:create_app', '--factory', '--host', '0.0.0.0',
                 '--port', str(args.port), '--ssl-keyfile', 'infra/certs/server-key.pem', '--ssl-certfile',
                 'infra/certs/server.pem', '--ws-max-size', '300000', '--no-access-log']):
                children.append(subprocess.Popen(command, cwd=ROOT, creationflags=flags))
        else:
            run(compose_command(True) + ['up', '-d', *build])
            # Retire the unused reference container if a previous run started it.
            run(compose_command() + ['stop', 'matlab-engine'])
        print('THE VAULT is running. Keep this terminal open; Ctrl+C releases its private MATLAB session.', flush=True)
        last_discovery = 0
        while worker.is_alive():
            if any(child.poll() is not None for child in children):
                raise MatlabSetupError('A local service exited. Check its startup output.')
            if time.monotonic() - last_discovery > 5:
                advertisement.refresh()
                last_discovery = time.monotonic()
            time.sleep(0.5)
        raise MatlabSetupError('The scoring service stopped unexpectedly.')
    finally:
        advertisement.close()
        for child in children:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
        server.should_exit = True
        worker.join(timeout=30)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nLocal scoring stopped. Docker infrastructure, if used, remains installed.')
    except (MatlabSetupError, subprocess.CalledProcessError, OSError) as exc:
        print(f'THE VAULT could not start: {exc}', file=sys.stderr)
        raise SystemExit(1)
