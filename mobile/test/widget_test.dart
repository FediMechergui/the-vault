import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:the_vault/api.dart';
import 'package:the_vault/main.dart';

void main() {
  testWidgets('home fits a small phone and consent blocks camera enrollment', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.runAsync(() async {
      final font = FontLoader('SpaceGrotesk')
        ..addFont(rootBundle.load('assets/fonts/SpaceGrotesk.ttf'));
      await font.load();
      await Future<void>.delayed(const Duration(milliseconds: 50));
    });
    final boundaryKey = GlobalKey();
    await tester.pumpWidget(
      RepaintBoundary(
        key: boundaryKey,
        child: VaultApp(api: VaultApi(), initialize: false),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Maximum security.'), findsOneWidget);
    expect(tester.takeException(), isNull);
    if (const bool.fromEnvironment('SCREENSHOTS')) {
      final boundary =
          boundaryKey.currentContext!.findRenderObject()!
              as RenderRepaintBoundary;
      await tester.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: 2);
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        await File('../docs/mobile-home.png')
            .writeAsBytes(bytes!.buffer.asUint8List());
      });
    }
    await tester.ensureVisible(find.text('Create your vault'));
    await tester.tap(find.text('Create your vault'));
    await tester.pumpAndSettle();
    expect(find.text('Your body.\nYour permission.'), findsOneWidget);
    final consentButton = find.widgetWithText(
      FilledButton,
      'I’m in. Create my vault.',
    );
    expect(tester.widget<FilledButton>(consentButton).onPressed, isNull);
    await tester.ensureVisible(find.byType(CheckboxListTile));
    await tester.tap(find.byType(Checkbox));
    await tester.pumpAndSettle();
    expect(tester.widget<FilledButton>(consentButton).onPressed, isNotNull);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpAndSettle();
  });
}
