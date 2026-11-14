import 'package:flutter_test/flutter_test.dart';
import 'package:the_vault/network/discovery.dart';
import 'package:the_vault/api.dart';

void main() {
  final record = <String, dynamic>{
    'id': '12345678-1234-1234-1234-123456789abc',
    'name': 'Computer',
    'host': '192.168.1.20',
    'port': 8443,
    'sha256': 'a' * 64,
  };
  test('A changed certificate or different computer cannot receive saved credentials', () async {
    final original = VaultServer.parse(record)!;
    final api = VaultApi()
      ..serverId = original.id
      ..fingerprint = original.fingerprint
      ..managementToken = 'test-device-credential';
    final changed = VaultServer.parse({...record, 'sha256': 'b' * 64})!;
    final stranger = VaultServer.parse({
      ...record,
      'id': '87654321-1234-1234-1234-123456789abc',
    })!;
    await expectLater(
      api.connectServer(changed),
      throwsA(isA<VaultException>()),
    );
    await expectLater(
      api.connectServer(stranger),
      throwsA(isA<VaultException>()),
    );
    expect(api.fingerprint, original.fingerprint);
    expect(api.serverId, original.id);
  });
  test(
    'Discovery accepts LAN endpoints and rejects public hosts or invalid pins',
    () {
      expect(VaultServer.parse(record)?.url, 'https://192.168.1.20:8443');
      for (final host in [
        '8.8.8.8',
        '127.0.0.1',
        '192.168.1.999',
        'example.com',
      ]) {
        expect(VaultServer.parse({...record, 'host': host}), isNull);
      }
      expect(
        VaultServer.parse({...record, 'sha256': 'not-a-certificate-pin'}),
        isNull,
      );
      expect(VaultServer.parse({...record, 'port': 0}), isNull);
    },
  );
  test('Remembered computer follows address changes and never switches to a stranger', () {
    final first = VaultServer.parse(record)!;
    final moved = VaultServer.parse({...record, 'host': '10.0.0.25'})!;
    final other = VaultServer.parse({
      ...record,
      'id': '87654321-1234-1234-1234-123456789abc',
    })!;
    expect(
      chooseServer([moved, other], first.id)?.url,
      'https://10.0.0.25:8443',
    );
    expect(chooseServer([other], first.id), isNull);
    expect(chooseServer([first, other], null), isNull);
    expect(chooseServer([first], null), first);
  });
}
