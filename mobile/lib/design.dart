import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';

const ink = Color(0xFF10120F);
const surface = Color(0xFF1B1E19);
const lime = Color(0xFFDBF9A7);
const paper = Color(0xFFF1F2E9);
const muted = Color(0xFF92998C);
const line = Color(0xFF343B2E);
const motion = Cubic(0.22, 1, 0.36, 1);

ThemeData vaultTheme() => ThemeData(
  brightness: Brightness.dark,
  scaffoldBackgroundColor: ink,
  fontFamily: 'SpaceGrotesk',
  colorScheme: const ColorScheme.dark(
    primary: lime,
    onPrimary: ink,
    surface: surface,
    onSurface: paper,
  ),
  textTheme: const TextTheme(
    bodyMedium: TextStyle(fontSize: 15, height: 1.55, color: paper),
    bodySmall: TextStyle(fontSize: 12, height: 1.5, color: muted),
    headlineLarge: TextStyle(
      fontSize: 44,
      fontWeight: FontWeight.w500,
      height: 1.03,
      letterSpacing: -2,
    ),
    headlineMedium: TextStyle(
      fontSize: 32,
      fontWeight: FontWeight.w500,
      height: 1.12,
      letterSpacing: -1,
    ),
    titleLarge: TextStyle(
      fontSize: 23,
      fontWeight: FontWeight.w500,
      letterSpacing: -0.5,
    ),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: surface,
    contentPadding: const EdgeInsets.all(20),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(20),
      borderSide: BorderSide.none,
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(20),
      borderSide: const BorderSide(color: lime),
    ),
  ),
  snackBarTheme: const SnackBarThemeData(
    backgroundColor: lime,
    contentTextStyle: TextStyle(color: ink),
  ),
);

class Eyebrow extends StatelessWidget {
  final String text;
  final Color color;
  const Eyebrow(this.text, {super.key, this.color = muted});
  @override
  Widget build(BuildContext context) => Text(
    text.toUpperCase(),
    style: TextStyle(
      fontSize: 10,
      height: 1.5,
      letterSpacing: 2.1,
      color: color,
      fontWeight: FontWeight.w600,
    ),
  );
}

class VaultButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final bool secondary;
  final bool busy;
  const VaultButton(
    this.text, {
    super.key,
    this.onPressed,
    this.secondary = false,
    this.busy = false,
  });
  @override
  Widget build(BuildContext context) => SizedBox(
    width: double.infinity,
    height: 62,
    child: FilledButton(
      onPressed: busy ? null : onPressed,
      style: FilledButton.styleFrom(
        backgroundColor: secondary ? surface : lime,
        foregroundColor: secondary ? paper : ink,
        disabledBackgroundColor: line,
        padding: const EdgeInsets.only(left: 24, right: 10),
        shape: const StadiumBorder(),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
          ),
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: secondary ? line : ink.withValues(alpha: 0.08),
            ),
            child: Center(
              child: busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: muted,
                      ),
                    )
                  : const Text('↗', style: TextStyle(fontSize: 24)),
            ),
          ),
        ],
      ),
    ),
  );
}

class Bezel extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;
  const Bezel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(22),
  });
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(4),
    decoration: BoxDecoration(
      color: const Color(0xFF2A2F25),
      borderRadius: BorderRadius.circular(28),
    ),
    child: Container(
      padding: padding,
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(24),
      ),
      child: child,
    ),
  );
}

class Glyph extends StatelessWidget {
  final String name;
  final double size;
  final Color color;
  const Glyph(this.name, {super.key, this.size = 24, this.color = paper});
  @override
  Widget build(BuildContext context) =>
      CustomPaint(size: Size.square(size), painter: _GlyphPainter(name, color));
}

class _GlyphPainter extends CustomPainter {
  final String name;
  final Color color;
  _GlyphPainter(this.name, this.color);
  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.width / 24);
    final p = Paint()
      ..color = color
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    if (name == 'face') {
      canvas.drawOval(const Rect.fromLTWH(5, 2, 14, 20), p);
      canvas.drawLine(const Offset(8, 9), const Offset(9, 9), p);
      canvas.drawLine(const Offset(15, 9), const Offset(16, 9), p);
      canvas.drawArc(
        const Rect.fromLTWH(8, 11, 8, 6),
        0.1,
        math.pi - 0.2,
        false,
        p,
      );
    } else if (name == 'body') {
      canvas.drawCircle(const Offset(12, 4), 2.5, p);
      canvas.drawPath(
        Path()
          ..moveTo(4, 8)
          ..lineTo(12, 10)
          ..lineTo(20, 6)
          ..moveTo(12, 8)
          ..lineTo(12, 15)
          ..lineTo(7, 22)
          ..moveTo(12, 15)
          ..lineTo(18, 21),
        p,
      );
    } else if (name == 'hand') {
      canvas.drawPath(
        Path()
          ..moveTo(6, 21)
          ..cubicTo(2, 17, 2, 14, 4, 13)
          ..lineTo(7, 16)
          ..lineTo(7, 4)
          ..quadraticBezierTo(9, 1, 10, 4)
          ..lineTo(10, 12)
          ..lineTo(11, 7)
          ..quadraticBezierTo(13, 5, 14, 8)
          ..lineTo(14, 12)
          ..quadraticBezierTo(17, 8, 18, 12)
          ..quadraticBezierTo(22, 12, 21, 16)
          ..lineTo(18, 22),
        p,
      );
    } else if (name == 'settings') {
      for (var i = 0; i < 3; i++) {
        final y = 5.0 + i * 7;
        canvas.drawLine(Offset(3, y), Offset(21, y), p);
        canvas.drawCircle(Offset(i == 1 ? 15 : 8, y), 2, Paint()..color = ink);
        canvas.drawCircle(Offset(i == 1 ? 15 : 8, y), 2, p);
      }
    } else if (name == 'check') {
      canvas.drawPath(
        Path()
          ..moveTo(4, 12)
          ..lineTo(10, 18)
          ..lineTo(21, 5),
        p,
      );
    } else {
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          const Rect.fromLTWH(3, 3, 18, 18),
          const Radius.circular(4),
        ),
        p,
      );
      canvas.drawCircle(const Offset(12, 12), 5, p);
      canvas.drawLine(const Offset(7, 12), const Offset(17, 12), p);
      canvas.drawLine(const Offset(12, 7), const Offset(12, 17), p);
    }
  }

  @override
  bool shouldRepaint(covariant _GlyphPainter old) =>
      old.name != name || old.color != color;
}

class VaultDoor extends StatelessWidget {
  final double rotation;
  final double size;
  const VaultDoor({super.key, this.rotation = 0, this.size = 280});
  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Three-lock vault door',
    child: CustomPaint(
      size: Size.square(size),
      painter: _DoorPainter(rotation),
    ),
  );
}

class _DoorPainter extends CustomPainter {
  final double rotation;
  _DoorPainter(this.rotation);
  @override
  void paint(Canvas c, Size size) {
    c.translate(size.width / 2, size.height / 2);
    c.scale(size.width / 300);
    c.drawCircle(Offset.zero, 137, Paint()..color = const Color(0xFF252B20));
    c.drawCircle(
      Offset.zero,
      132,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF555D4A), Color(0xFF1A1E16), Color(0xFF333B2B)],
        ).createShader(const Rect.fromLTWH(-132, -132, 264, 264)),
    );
    c.drawCircle(Offset.zero, 121, Paint()..color = ink);
    c.drawCircle(
      Offset.zero,
      117,
      Paint()
        ..shader = const RadialGradient(
          colors: [Color(0xFF343B2C), Color(0xFF22271D)],
        ).createShader(const Rect.fromLTWH(-117, -117, 234, 234)),
    );
    final tick = Paint()
      ..color = const Color(0xFF5A644D)
      ..strokeWidth = 1;
    for (var i = 0; i < 60; i++) {
      final a = i * math.pi / 30;
      final inner = i % 5 == 0 ? 100.0 : 105.0;
      c.drawLine(
        Offset(math.cos(a) * inner, math.sin(a) * inner),
        Offset(math.cos(a) * 110, math.sin(a) * 110),
        tick,
      );
    }
    for (var i = 0; i < 3; i++) {
      final angle = i * math.pi * 2 / 3 - math.pi / 2;
      c.drawCircle(
        Offset(math.cos(angle) * 126, math.sin(angle) * 126),
        4,
        Paint()..color = lime,
      );
    }
    c.save();
    c.rotate(rotation);
    final p = Paint()
      ..color = const Color(0xFF5E6952)
      ..strokeWidth = 11
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < 3; i++) {
      final a = i * math.pi * 2 / 3;
      c.drawLine(
        Offset(math.cos(a) * 26, math.sin(a) * 26),
        Offset(math.cos(a) * 70, math.sin(a) * 70),
        p,
      );
    }
    c.drawCircle(
      Offset.zero,
      74,
      Paint()
        ..color = const Color(0xFF839171)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4,
    );
    c.drawCircle(
      Offset.zero,
      69,
      Paint()
        ..color = const Color(0xFF14190F)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
    c.drawCircle(Offset.zero, 29, Paint()..color = const Color(0xFF424D35));
    c.drawCircle(
      Offset.zero,
      25,
      Paint()
        ..color = const Color(0xFF899A6F)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );
    c.drawCircle(Offset.zero, 4, Paint()..color = lime);
    c.restore();
  }

  @override
  bool shouldRepaint(covariant _DoorPainter old) => old.rotation != rotation;
}
