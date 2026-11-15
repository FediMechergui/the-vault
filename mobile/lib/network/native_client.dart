import 'dart:async';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:http/io_client.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

Future<HttpClient> _trustedClient(String? fingerprint) async {
  final client = HttpClient(
    context: SecurityContext(withTrustedRoots: fingerprint == null),
  );
  client.connectionTimeout = const Duration(seconds: 10);
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
  final client = await _trustedClient(fingerprint);
  try {
    final socket = await WebSocket.connect(uri.toString(), customClient: client)
        .timeout(
          const Duration(seconds: 12),
          onTimeout: () {
            throw TimeoutException('Opening the camera stream timed out');
          },
        );
    return IOWebSocketChannel(socket);
  } catch (_) {
    client.close(force: true);
    rethrow;
  }
}

String? transportError(Object error) {
  if (error is HandshakeException) {
    return 'The secure connection could not verify the PC certificate. Check both devices’ date and time, then find your paired computer again.';
  }
  if (error is SocketException) {
    return 'The PC connection failed${error.osError == null ? '' : ' (network code ${error.osError!.errorCode})'}. Keep the server running and check the Wi-Fi connection.';
  }
  if (error is WebSocketException) {
    return 'The PC could not open the camera stream. Check the server terminal and start a fresh take.';
  }
  return null;
}
