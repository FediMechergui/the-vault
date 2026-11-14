"""Idempotent development setup: credentials, TLS, gRPC bindings and bundled meme."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import ipaddress
import secrets
import subprocess
import sys
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]


def generate_protocol():
    subprocess.run([sys.executable, "-m", "grpc_tools.protoc", "-I.", "--python_out=.",
                    "--grpc_python_out=.", "contracts/vision.proto"], cwd=ROOT, check=True)


def make_meme():
    path = ROOT / "assets" / "original-meme.png"
    if not path.is_file():
        raise FileNotFoundError(f"Restore the bundled captioned meme: {path}")


def certificates(host, force=False):
    folder = ROOT / "infra" / "certs"
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "server.pem").exists() and not force:
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "THE VAULT development")])
    names = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
             x509.IPAddress(ipaddress.ip_address("10.0.2.2"))]
    if host:
        names.append(x509.IPAddress(ipaddress.ip_address(host)))
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=5))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(names), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256()))
    (folder / "server-key.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    pem = certificate.public_bytes(serialization.Encoding.PEM)
    (folder / "server.pem").write_bytes(pem)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="Your PC's LAN IPv4 address, for phone TLS")
    parser.add_argument("--renew-cert", action="store_true")
    parser.add_argument("--models", action="store_true")
    args = parser.parse_args()
    env = ROOT / ".env"
    if not env.exists():
        values = {"JWT_SECRET": secrets.token_hex(32), "TEMPLATE_KEY": secrets.token_hex(32),
                  "ADMIN_KEY": secrets.token_hex(32), "PG_PASSWORD": secrets.token_hex(24),
                  "S3_ACCESS_KEY": "vault-local", "S3_SECRET_KEY": secrets.token_hex(24)}
        env.write_text("\n".join(f"{k}={v}" for k, v in values.items()) + "\n")
    (ROOT / ".local").mkdir(exist_ok=True)
    generate_protocol()
    make_meme()
    certificates(args.host, args.renew_cert)
    if args.models:
        from download_models import download
        download()
    print("THE VAULT setup complete. Credentials remain in .env; do not commit them.")


if __name__ == "__main__":
    main()
