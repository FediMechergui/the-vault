import uuid
from cryptography import x509
from cryptography.hazmat.primitives import hashes

from scripts import bootstrap, discovery


def test_server_identity_survives_address_changes(tmp_path):
    first = discovery.server_identity(tmp_path)
    assert str(uuid.UUID(first)) == first
    assert discovery.server_identity(tmp_path) == first
    assert discovery.server_identity(tmp_path / 'other') != first


def test_advertisement_contains_public_identity_and_tracks_ip(monkeypatch, tmp_path):
    monkeypatch.setattr(bootstrap, 'ROOT', tmp_path)
    bootstrap.certificates(None)
    events = []

    class Transport:
        def __init__(self, **kwargs): pass
        def register_service(self, info): events.append(('register', info))
        def update_service(self, info): events.append(('update', info))
        def unregister_service(self, info): events.append(('remove', info))
        def close(self): events.append(('close', None))

    monkeypatch.setattr(discovery, 'Zeroconf', Transport)
    monkeypatch.setattr(discovery, 'lan_addresses', lambda: ['192.168.1.5'])
    advert = discovery.LanAdvertisement(tmp_path)
    advert.refresh()
    original = advert.info
    certificate = x509.load_pem_x509_certificate((tmp_path / 'infra/certs/server.pem').read_bytes())
    assert original.properties[b'sha256'].decode() == certificate.fingerprint(hashes.SHA256()).hex()
    assert set(original.properties) == {b'id', b'sha256', b'name', b'version'}
    monkeypatch.setattr(discovery, 'lan_addresses', lambda: ['192.168.1.6'])
    advert.refresh()
    assert advert.info.properties[b'id'] == original.properties[b'id']
    assert advert.info.parsed_addresses() == ['192.168.1.6']
    advert.close()
    assert [event[0] for event in events] == ['register', 'update', 'remove', 'close']
