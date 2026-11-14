import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';
import 'package:camera_android/camera_android.dart';

import 'api.dart';
import 'design.dart';
import 'screens.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    AndroidCamera.registerWith();
  }
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      systemNavigationBarColor: ink,
    ),
  );
  runApp(VaultApp(api: VaultApi()));
}

class VaultApp extends StatelessWidget {
  final VaultApi api;
  final bool initialize;
  const VaultApp({super.key, required this.api, this.initialize = true});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'THE VAULT',
    debugShowCheckedModeBanner: false,
    theme: vaultTheme(),
    home: VaultHome(api: api, initialize: initialize),
  );
}
