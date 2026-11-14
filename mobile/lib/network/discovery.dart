import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

class VaultServer {
  final String id, name, host, fingerprint;
  final int port;
  const VaultServer({
    required this.id,
    required this.name,
    required this.host,
    required this.fingerprint,
    required this.port,
  });

  String get url => 'https://$host:$port';

  static VaultServer? parse(Map<dynamic, dynamic> value) {
    final id = value['id'], host = value['host'], pin = value['sha256'];
    final port = value['port'];
    if (id is! String ||
        !RegExp(r'^[a-f0-9-]{36}$').hasMatch(id) ||
        host is! String ||
        pin is! String ||
        !RegExp(r'^[a-f0-9]{64}$').hasMatch(pin) ||
        port is! int ||
        port < 1 ||
        port > 65535) {
      return null;
    }
    final parts = host.split('.').map(int.tryParse).toList();
    if (parts.length != 4 || parts.any((v) => v == null || v < 0 || v > 255)) {
      return null;
    }
    final local =
        parts[0] == 10 ||
        (parts[0] == 192 && parts[1] == 168) ||
        (parts[0] == 172 && parts[1]! >= 16 && parts[1]! <= 31);
    if (!local) return null;
    return VaultServer(
      id: id,
      name: value['name'] is String ? value['name'] : 'THE VAULT',
      host: host,
      fingerprint: pin,
      port: port,
    );
  }
}

VaultServer? chooseServer(List<VaultServer> servers, String? rememberedId) {
  if (rememberedId != null) {
    for (final server in servers) {
      if (server.id == rememberedId) return server;
    }
    return null;
  }
  return servers.length == 1 ? servers.single : null;
}

Future<List<VaultServer>> discoverServers() async {
  if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return [];
  const channel = MethodChannel('dev.thevault/discovery');
  final values = await channel.invokeListMethod<dynamic>('discover');
  final found = <String, VaultServer>{};
  for (final value in values ?? []) {
    if (value is Map) {
      final server = VaultServer.parse(value);
      if (server != null) found[server.id] = server;
    }
  }
  return found.values.toList();
}
