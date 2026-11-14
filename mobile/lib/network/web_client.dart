import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

Future<http.Client> createClient({String? fingerprint}) async => http.Client();
Future<WebSocketChannel> connectSocket(Uri uri, {String? fingerprint}) async {
  final channel = WebSocketChannel.connect(uri);
  await channel.ready;
  return channel;
}
