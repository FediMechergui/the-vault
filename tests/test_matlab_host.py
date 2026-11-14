"""Host discovery and transport tests; Engine doubles do not prove a MATLAB license."""
import asyncio
import importlib
import json
import os
from pathlib import Path
import socket
import ssl
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

import matlab_host as host
import service
from gateway.app.clients import ScoringClient
from scripts import start
from .samples import capture


def installation(tmp_path, name='MATLAB R2025b'):
    root = tmp_path / name
    (root / 'bin').mkdir(parents=True)
    (root / 'bin/matlab.exe').touch()
    (root / 'extern/engines/python').mkdir(parents=True)
    return root.resolve()


@pytest.fixture(autouse=True)
def no_real_matlab(monkeypatch):
    monkeypatch.delenv('MATLAB_ROOT', raising=False)
    monkeypatch.setattr(host.shutil, 'which', lambda _: None)
    monkeypatch.setattr(host, 'standard_roots', lambda: [])


def test_auto_uses_installation_and_explicit_root_wins(tmp_path, monkeypatch):
    older = installation(tmp_path, 'R2025a')
    newer = installation(tmp_path, 'R2026b')
    monkeypatch.setattr(host, 'standard_roots', lambda: [older, newer])
    assert host.select_backend()[1].root == newer
    monkeypatch.setenv('MATLAB_ROOT', str(older))
    assert host.select_backend()[1].root == older
    assert host.select_backend(root=str(newer))[1].root == newer
    assert host.select_backend('python-reference') == ('python-reference', None)


def test_path_installation_and_missing_or_partial_installs(tmp_path, monkeypatch):
    partial = tmp_path / 'R2026b'
    partial.mkdir()
    monkeypatch.setattr(host, 'standard_roots', lambda: [partial])
    assert host.select_backend() == ('python-reference', None)
    with pytest.raises(host.MatlabSetupError, match='No complete'):
        host.select_backend('matlab-engine')
    with pytest.raises(host.MatlabSetupError, match='not a complete'):
        host.select_backend(root=str(partial))
    root = installation(tmp_path)
    monkeypatch.setattr(host.shutil, 'which', lambda _: str(root / 'bin/matlab.exe'))
    assert host.select_backend()[1].root == root


def test_shipped_engine_avoids_installer_and_preserves_license_environment(tmp_path, monkeypatch):
    root = installation(tmp_path)
    package = root / 'extern/engines/python/dist/matlab/engine'
    package.mkdir(parents=True)
    (package / '__init__.py').touch()
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        assert kwargs['env']['MLM_LICENSE_FILE'] == 'existing-test-server'
        return SimpleNamespace(returncode=0)
    monkeypatch.setenv('MLM_LICENSE_FILE', 'existing-test-server')
    monkeypatch.setattr(host.subprocess, 'run', run)
    env = host.prepare_engine(host.Installation(root), tmp_path)
    assert len(calls) == 1 and calls[0][-1] == 'import matlab.engine'
    assert str(root / 'extern/engines/python/dist') in env['PYTHONPATH']
    assert not (tmp_path / '.local').exists()  # No license cache or credential copy.


class Engine:
    def __init__(self, root, fail=False):
        self.root, self.fail, self.closed = root, fail, False
    def matlabroot(self, **kwargs):
        return str(self.root)
    def addpath(self, path, **kwargs):
        self.path = path
    def vault_engine_check(self, **kwargs):
        if self.fail:
            raise RuntimeError('Test double: toolbox unavailable')
        return json.dumps({'release': 'R2025b', 'license_source': 'current-user'})
    def quit(self):
        self.closed = True


def mock_engine_import(monkeypatch, start_matlab):
    original = importlib.import_module
    monkeypatch.setattr(host.importlib, 'import_module', lambda name: SimpleNamespace(start_matlab=start_matlab)
                        if name == 'matlab.engine' else original(name))


def test_license_failure_never_silently_substitutes_python(monkeypatch):
    def denied(*args):
        raise RuntimeError('Test double: no available license')
    mock_engine_import(monkeypatch, denied)
    monkeypatch.setattr(service, 'MODE', 'matlab-engine')
    with pytest.raises(host.MatlabSetupError, match='existing license'):
        with TestClient(service.app):
            pass
    assert service.MODE == 'matlab-engine'
    assert service.runtime is None


@pytest.mark.parametrize('wrong_root,missing_toolbox', [(True, False), (False, True)])
def test_failed_preflight_releases_private_engine(tmp_path, monkeypatch, wrong_root, missing_toolbox):
    root = installation(tmp_path)
    monkeypatch.setenv('MATLAB_ROOT', str(root))
    engine = Engine(tmp_path if wrong_root else root, missing_toolbox)
    mock_engine_import(monkeypatch, lambda options: engine)
    with pytest.raises(host.MatlabSetupError):
        host.open_engine()
    assert engine.closed


def test_engine_health_and_normal_shutdown(tmp_path, monkeypatch):
    root = installation(tmp_path)
    engine = Engine(root)
    mock_engine_import(monkeypatch, lambda options: engine)
    monkeypatch.setattr(service, 'MODE', 'matlab-engine')
    monkeypatch.setenv('SCORING_TOKEN', 'test-scoring-token')
    with TestClient(service.app) as client:
        assert client.get('/health').status_code == 401
        reply = client.get('/health', headers={'X-Scoring-Key': 'test-scoring-token'})
        assert reply.json() == {'ready': True, 'engine': 'matlab-engine', 'matlab': True,
                                'release': 'R2025b', 'license_source': 'current-user'}
        assert not engine.closed
    assert engine.closed and service.runtime is None


def test_live_host_tls_and_gateway_authentication(tmp_path, monkeypatch):
    monkeypatch.setattr(start, 'ROOT', tmp_path)
    monkeypatch.setattr(service, 'MODE', 'python-reference')
    monkeypatch.setenv('SCORING_TOKEN', 'transport-test-token')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server, worker, cert = start.start_scoring('python-reference', port, '127.0.0.1', 10)
    try:
        url = f'https://127.0.0.1:{port}'
        verify = ssl.create_default_context(cafile=str(cert))
        with httpx.Client(verify=verify) as direct:
            assert direct.get(url + '/health').status_code == 401
            assert direct.get(url + '/health', headers={'X-Scoring-Key': 'wrong'}).status_code == 401
        async def roundtrip():
            client = ScoringClient(url, 'transport-test-token', str(cert))
            try:
                assert (await client.health())['engine'] == 'python-reference'
                enrolled = await client.call('enroll', 'face', captures=[capture('face', i) for i in range(2)])
                result = await client.call('score', 'face', capture=capture('face', 0), template=enrolled['template'])
                assert result['passed'] and result['engine'] == 'python-reference'
            finally:
                await client.close()
        asyncio.run(roundtrip())
    finally:
        server.should_exit = True
        worker.join(timeout=10)
    assert not worker.is_alive()


def test_check_is_read_only_and_does_not_claim_license(monkeypatch, capsys):
    monkeypatch.setattr(start, 'run', lambda command: pytest.fail('check must not start services'))
    assert start.main(['--check']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['backend'] == 'python-reference'
    assert result['license_checked'] is False
    assert result['compiler_sdk_required'] is False
