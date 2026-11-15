import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import 'network/platform_client.dart';
import 'network/discovery.dart';

class VaultApi {
  final FlutterSecureStorage storage;
  VaultApi({this.storage = const FlutterSecureStorage()});
  String baseUrl = const String.fromEnvironment(
    'VAULT_SERVER',
    defaultValue: kIsWeb ? 'https://localhost:8443' : 'https://10.0.2.2:8443',
  );
  String? managementToken;
  String? accessToken;
  Map<String, dynamic>? profile;
  String? serverId, serverName, fingerprint;
  String? connectionNotice;
  http.Client? _client;
  Future<void> initialize() async {
    baseUrl = await storage.read(key: 'server') ?? baseUrl;
    managementToken = await storage.read(key: 'management');
    serverId = await storage.read(key: 'server_id');
    serverName = await storage.read(key: 'server_name');
    fingerprint = await storage.read(key: 'server_pin');
    try {
      await findServers();
    } catch (e) {
      connectionNotice = friendlyError(e);
    }
    _client ??= await createClient(fingerprint: fingerprint);
    if (managementToken != null) {
      try {
        await refreshProfile();
      } catch (_) {
        /* Retry when the server is available. */
      }
    }
  }

  Future<List<VaultServer>> findServers() async {
    final servers = await discoverServers();
    final selected = chooseServer(servers, serverId);
    if (selected != null) {
      await connectServer(selected);
    } else {
      connectionNotice = servers.isEmpty
          ? 'Start THE VAULT on your computer and join the same Wi-Fi.'
          : serverId != null
          ? 'Your paired computer is not available on this network.'
          : 'Several computers are available. Choose yours in Settings.';
    }
    return servers;
  }

  Future<void> connectServer(VaultServer server) async {
    if (server.id == serverId &&
        fingerprint != null &&
        server.fingerprint != fingerprint) {
      throw VaultException(
        'This computer’s identity has changed. Restore its original certificate before reconnecting.',
      );
    }
    if (managementToken != null && server.id != serverId) {
      throw VaultException(
        'Delete this device’s current vault before pairing a different computer.',
      );
    }
    final candidate = await createClient(fingerprint: server.fingerprint);
    try {
      final response = await candidate
          .get(Uri.parse('${server.url}/api/v1/health'))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode != 200 ||
          jsonDecode(response.body)['ready'] != true) {
        throw VaultException(
          'Your computer was found, but its server is still starting. Try again shortly.',
        );
      }
    } catch (_) {
      candidate.close();
      rethrow;
    }
    _client?.close();
    _client = candidate;
    baseUrl = server.url;
    serverId = server.id;
    serverName = server.name;
    fingerprint = server.fingerprint;
    connectionNotice = 'Connected to ${server.name}';
    await storage.write(key: 'server', value: baseUrl);
    await storage.write(key: 'server_id', value: serverId);
    await storage.write(key: 'server_name', value: serverName);
    await storage.write(key: 'server_pin', value: fingerprint);
  }

  Future<void> ensureConnection() async {
    try {
      final client = _client ??= await createClient(fingerprint: fingerprint);
      final response = await client
          .get(Uri.parse('$baseUrl/api/v1/health'))
          .timeout(const Duration(seconds: 2));
      if (response.statusCode == 200 &&
          jsonDecode(response.body)['ready'] == true) {
        return;
      }
    } catch (_) {
      /* Rediscover the paired computer after an address change. */
    }
    final servers = await findServers();
    if (chooseServer(servers, serverId) == null) {
      throw VaultException(
        connectionNotice ?? 'Start your computer’s server on the same Wi-Fi.',
      );
    }
  }

  Future<Map<String, dynamic>> request(
    String method,
    String path, {
    Map<String, dynamic>? data,
    bool vault = false,
    String? sessionToken,
  }) async {
    final client = _client ??= await createClient(fingerprint: fingerprint);
    final req = http.Request(method, Uri.parse('$baseUrl$path'));
    req.headers['Content-Type'] = 'application/json';
    final credential = vault ? accessToken : managementToken;
    if (credential != null) req.headers['Authorization'] = 'Bearer $credential';
    if (sessionToken != null) req.headers['X-Session-Token'] = sessionToken;
    if (data != null) req.body = jsonEncode(data);
    final response = await client
        .send(req)
        .then(http.Response.fromStream)
        .timeout(const Duration(seconds: 20));
    final body = response.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 400) {
      final detail = body['detail'];
      throw VaultException(
        detail is String
            ? detail
            : detail is Map
            ? '${detail['message'] ?? 'Request failed'}${detail['retry_after'] != null ? '. Retry in ${detail['retry_after']} seconds.' : ''}'
            : 'Could not complete this request. Check your details.',
      );
    }
    return body;
  }

  Future<void> register(String pseudo) async {
    await ensureConnection();
    final result = await request(
      'POST',
      '/api/v1/users',
      data: {'pseudo': pseudo, 'consent': true},
    );
    managementToken = result['management_token'];
    await storage.write(key: 'management', value: managementToken);
    await refreshProfile();
  }

  Future<void> refreshProfile() async {
    profile = await request('GET', '/api/v1/users/me');
  }

  Future<void> setServer(String value) async {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        uri.scheme != 'https' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.query.isNotEmpty ||
        uri.fragment.isNotEmpty ||
        (uri.path.isNotEmpty && uri.path != '/')) {
      throw VaultException(
        'Enter an HTTPS server address, such as https://192.168.1.20:8443',
      );
    }
    final next = value.trim().replaceAll(RegExp(r'/$'), '');
    if (next != baseUrl && managementToken != null) {
      throw VaultException(
        'Delete this device’s current vault before connecting to a different server.',
      );
    }
    baseUrl = next;
    _client?.close();
    _client = null;
    await storage.write(key: 'server', value: baseUrl);
  }

  Future<Map<String, dynamic>> start(String layer, bool enrollment) async {
    await ensureConnection();
    return request(
      'POST',
      enrollment ? '/api/v1/enroll/$layer/start' : '/api/v1/auth/start',
      data: {'user_id': profile!['id']},
    );
  }

  Future<WebSocketChannel> stream(String sessionId, String token) async {
    final uri = Uri.parse(baseUrl)
        .replace(scheme: 'wss', path: '/ws/stream/$sessionId');
    final channel = await connectSocket(uri, fingerprint: fingerprint);
    channel.sink.add(jsonEncode({'token': token}));
    return channel;
  }

  Future<Uint8List> image(String path) async {
    final client = _client ??= await createClient(fingerprint: fingerprint);
    final response = await client.get(Uri.parse('$baseUrl$path'));
    if (response.statusCode != 200) {
      throw VaultException('This reveal has expired. Open your vault again.');
    }
    return response.bodyBytes;
  }

  Future<void> deleteAccount() async {
    await request('DELETE', '/api/v1/users/${profile!['id']}');
    await storage.delete(key: 'management');
    profile = null;
    managementToken = null;
    accessToken = null;
  }
}

class VaultException implements Exception {
  final String message;
  VaultException(this.message);
  @override
  String toString() => message;
}

String friendlyError(Object error) {
  if (error is VaultException) return error.message;
  if (error is TimeoutException) {
    return 'The PC took too long to respond. Check its server terminal, then retry. Your take was not confirmed.';
  }
  final transport = transportError(error);
  if (transport != null) return transport;
  if (error is http.ClientException || error is WebSocketChannelException) {
    return 'The PC connection was interrupted. Keep the server running, check Wi-Fi, then start a fresh take.';
  }
  if (error is FormatException) {
    return 'The PC returned an unreadable response. Check its server terminal and update the server.';
  }
  return 'Could not complete this action (${error.runtimeType}). Go back and retry.';
}
