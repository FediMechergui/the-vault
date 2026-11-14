import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:http/io_client.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

Future<HttpClient> _trustedClient(String? fingerprint) async {
  final client = HttpClient(
    context: SecurityContext(withTrustedRoots: fingerprint == null),
  );
  if (fingerprint != null) {
    // With no system roots, every discovered server must match its saved pin.
    client.badCertificateCallback = (certificate, host, port) =>
        sha256.convert(certificate.der).toString() == fingerprint &&
        DateTime.now().isAfter(certificate.startValidity) &&
        DateTime.now().isBefore(certificate.endValidity);
  }
  return client;
}

Future<IOClient> createClient({String? fingerprint}) async =>
    IOClient(await _trustedClient(fingerprint));
Future<WebSocketChannel> connectSocket(Uri uri, {String? fingerprint}) async {
  final socket = await WebSocket.connect(
    uri.toString(),
    customClient: await _trustedClient(fingerprint),
  );
  return IOWebSocketChannel(socket);
}
