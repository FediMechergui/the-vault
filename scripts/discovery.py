"""Advertise this PC's HTTPS gateway with mDNS; publish only its public identity."""
import ipaddress
from pathlib import Path
import socket
import uuid

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from zeroconf import IPVersion, ServiceInfo, Zeroconf

SERVICE_TYPE = '_thevault._tcp.local.'


def lan_addresses():
    # UDP connect selects the default route without sending a packet.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('8.8.8.8', 80))
            primary = sock.getsockname()[0]
        if ipaddress.ip_address(primary).is_private:
            return [primary]
    except OSError:
        pass
    import ifaddr
    return sorted({ip.ip for adapter in ifaddr.get_adapters() for ip in adapter.ips
                   if isinstance(ip.ip, str) and ipaddress.ip_address(ip.ip).is_private
                   and not ipaddress.ip_address(ip.ip).is_loopback
                   and not ipaddress.ip_address(ip.ip).is_link_local})


def server_identity(root):
    path = Path(root) / '.local/server-id'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return str(uuid.UUID(path.read_text().strip()))
    identity = str(uuid.uuid4())
    path.write_text(identity + '\n')
    return identity


class LanAdvertisement:
    def __init__(self, root, port=8443):
        self.root, self.port = Path(root), port
        self.identity = server_identity(root)
        self.name = socket.gethostname()[:40]
        certificate = x509.load_pem_x509_certificate((self.root / 'infra/certs/server.pem').read_bytes())
        self.fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
        self.addresses = []
        self.zeroconf = None
        self.info = None

    def refresh(self):
        addresses = lan_addresses()
        if addresses == self.addresses and self.zeroconf:
            return
        if not addresses:
            self.close()
            self.addresses = []
            return
        self.addresses = addresses
        self.info = ServiceInfo(SERVICE_TYPE, f'THE VAULT {self.identity[:8]}.{SERVICE_TYPE}',
            addresses=[socket.inet_aton(ip) for ip in addresses], port=self.port,
            properties={'id': self.identity, 'sha256': self.fingerprint, 'name': self.name, 'version': '1'},
            server=f'vault-{self.identity}.local.')
        if self.zeroconf is None:
            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self.zeroconf.register_service(self.info)
        else:
            self.zeroconf.update_service(self.info)
        print(f'Phone discovery ready: {self.name} at {", ".join(addresses)}:{self.port}', flush=True)

    def close(self):
        if self.zeroconf:
            if self.info:
                self.zeroconf.unregister_service(self.info)
            self.zeroconf.close()
            self.zeroconf = None
