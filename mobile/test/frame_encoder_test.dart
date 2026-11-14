import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as image;
import 'package:the_vault/frame_encoder.dart';

void main() {
  test('YUV conversion honors padded rows and portrait sensor rotation', () {
    final jpeg = encodeFrame({
      'width': 4,
      'height': 2,
      'planes': [
        Uint8List.fromList([
          120,
          120,
          120,
          120,
          0,
          0,
          120,
          120,
          120,
          120,
          0,
          0,
        ]),
        Uint8List.fromList([128, 0, 128, 0]),
        Uint8List.fromList([128, 0, 128, 0]),
      ],
      'strides': [6, 4, 4],
      'pixels': [1, 2, 2],
      'rotation': 90,
    });
    final decoded = image.decodeJpg(jpeg)!;
    expect(decoded.width, 2);
    expect(decoded.height, 4);
    expect(decoded.getPixel(0, 0).r, closeTo(120, 3));
    expect(decoded.getPixel(0, 0).g, closeTo(120, 3));
    expect(decoded.getPixel(0, 0).b, closeTo(120, 3));
  });
}
