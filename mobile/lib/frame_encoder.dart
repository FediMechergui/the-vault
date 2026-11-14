import 'dart:typed_data';

import 'package:image/image.dart' as img;

Uint8List encodeFrame(Map<String, dynamic> frame) {
  final width = frame['width'] as int, height = frame['height'] as int;
  final planes = (frame['planes'] as List).cast<Uint8List>();
  final strides = (frame['strides'] as List).cast<int>();
  final pixels = (frame['pixels'] as List).cast<int>();
  final factor = width > 640 ? width / 640 : 1.0;
  final w = (width / factor).round(), h = (height / factor).round();
  var image = img.Image(width: w, height: h);
  for (var y = 0; y < h; y++) {
    final sy = (y * factor).floor().clamp(0, height - 1);
    for (var x = 0; x < w; x++) {
      final sx = (x * factor).floor().clamp(0, width - 1);
      if (planes.length == 1) {
        final at = sy * strides[0] + sx * 4;
        image.setPixelRgb(
          x,
          y,
          planes[0][at + 2],
          planes[0][at + 1],
          planes[0][at],
        );
      } else {
        final yy = planes[0][sy * strides[0] + sx * pixels[0]].toDouble();
        final u =
            planes[1][(sy ~/ 2) * strides[1] + (sx ~/ 2) * pixels[1]] - 128.0;
        final v =
            planes[2][(sy ~/ 2) * strides[2] + (sx ~/ 2) * pixels[2]] - 128.0;
        image.setPixelRgb(
          x,
          y,
          (yy + 1.402 * v).round().clamp(0, 255),
          (yy - 0.344136 * u - 0.714136 * v).round().clamp(0, 255),
          (yy + 1.772 * u).round().clamp(0, 255),
        );
      }
    }
  }
  final rotation = frame['rotation'] as int;
  if (rotation != 0) image = img.copyRotate(image, angle: rotation);
  return Uint8List.fromList(img.encodeJpg(image, quality: 70));
}
