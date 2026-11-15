import 'dart:async';
import 'dart:convert';

import 'package:camera_platform_interface/camera_platform_interface.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:stream_channel/stream_channel.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:the_vault/api.dart';
import 'package:the_vault/capture_screen.dart';

class TestCamera extends CameraPlatform {
  final frames = StreamController<CameraImageData>.broadcast();
  final errors = StreamController<CameraErrorEvent>.broadcast();
  bool disposed = false;
  @override
  Future<List<CameraDescription>> availableCameras() async => [
    const CameraDescription(
      name: 'test',
      lensDirection: CameraLensDirection.front,
      sensorOrientation: 90,
    ),
  ];
  @override
  Future<int> createCamera(
    CameraDescription description,
    ResolutionPreset? resolution, {
    bool enableAudio = false,
  }) async => 1;
  @override
  Future<void> initializeCamera(
    int id, {
    ImageFormatGroup imageFormatGroup = ImageFormatGroup.unknown,
  }) async {}
  @override
  Stream<CameraInitializedEvent> onCameraInitialized(int id) => Stream.value(
    CameraInitializedEvent(
      id,
      640,
      480,
      ExposureMode.auto,
      false,
      FocusMode.auto,
      false,
    ),
  );
  @override
  Stream<CameraErrorEvent> onCameraError(int id) => errors.stream;
  @override
  Stream<DeviceOrientationChangedEvent> onDeviceOrientationChanged() =>
      const Stream.empty();
  @override
  Future<void> lockCaptureOrientation(
    int id,
    DeviceOrientation orientation,
  ) async {}
  @override
  bool supportsImageStreaming() => true;
  @override
  Stream<CameraImageData> onStreamedFrameAvailable(
    int id, {
    CameraImageStreamOptions? options,
  }) => frames.stream;
  @override
  Widget buildPreview(int id) => const SizedBox();
  @override
  Future<void> dispose(int id) async {
    disposed = true;
  }

  void frame() => frames.add(
    CameraImageData(
      format: const CameraImageFormat(ImageFormatGroup.yuv420, raw: 35),
      width: 4,
      height: 4,
      planes: [
        CameraImagePlane(
          bytes: Uint8List.fromList(List.filled(16, 120)),
          bytesPerRow: 4,
          bytesPerPixel: 1,
        ),
        CameraImagePlane(
          bytes: Uint8List.fromList(List.filled(4, 128)),
          bytesPerRow: 2,
          bytesPerPixel: 1,
        ),
        CameraImagePlane(
          bytes: Uint8List.fromList(List.filled(4, 128)),
          bytesPerRow: 2,
          bytesPerPixel: 1,
        ),
      ],
    ),
  );
}

class TestSocket extends StreamChannelMixin<dynamic>
    implements WebSocketChannel {
  final incoming = StreamController<dynamic>(sync: true);
  final outgoing = StreamController<dynamic>();
  late final TestSink output = TestSink(outgoing.sink);
  @override
  Stream<dynamic> get stream => incoming.stream;
  @override
  WebSocketSink get sink => output;
  @override
  Future<void> get ready async {}
  @override
  int? get closeCode => null;
  @override
  String? get closeReason => null;
  @override
  String? get protocol => null;
  void reply(Map<String, dynamic> message) => incoming.add(jsonEncode(message));
}

class TestSink implements WebSocketSink {
  final StreamSink<dynamic> delegate;
  bool closed = false;
  TestSink(this.delegate);
  @override
  void add(dynamic data) => delegate.add(data);
  @override
  void addError(Object error, [StackTrace? stackTrace]) =>
      delegate.addError(error, stackTrace);
  @override
  Future<void> addStream(Stream<dynamic> stream) => delegate.addStream(stream);
  @override
  Future<void> get done => delegate.done;
  @override
  Future<void> close([int? code, String? reason]) async {
    closed = true;
    await delegate.close();
  }
}

class CaptureApi extends VaultApi {
  final TestSocket socket;
  CaptureApi(this.socket);
  @override
  Future<WebSocketChannel> stream(String sessionId, String token) async =>
      socket;
}

void main() {
  late TestCamera camera;
  late TestSocket socket;
  late List<dynamic> sent;
  late CameraPlatform previous;
  setUp(() {
    previous = CameraPlatform.instance;
    CameraPlatform.instance = camera = TestCamera();
    socket = TestSocket();
    sent = [];
    socket.outgoing.stream.listen(sent.add);
  });
  tearDown(() {
    CameraPlatform.instance = previous;
  });

  Future<void> open(WidgetTester tester) async {
    tester.view.physicalSize = const Size(440, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(
        home: CaptureScreen(
          api: CaptureApi(socket),
          enrollment: true,
          session: {
            'session_id': 'test',
            'session_token': 'test',
            'challenge': {
              'layer': 'hand',
              'duration_ms': 8000,
              'liveness': null,
              'repetitions': 5,
            },
          },
        ),
      ),
    );
    await tester.pumpAndSettle();
    socket.reply({'type': 'ready'});
    await tester.pump();
    expect(tester.takeException(), isNull);
    expect(
      camera.disposed,
      isFalse,
      reason: tester
          .widgetList<Text>(find.byType(Text))
          .map((t) => t.data)
          .join('\n'),
    );
  }

  Future<void> sendFrame(WidgetTester tester) async {
    final before = sent.length;
    await tester.runAsync(() async {
      camera.frame();
      for (var i = 0; i < 100 && sent.length == before; i++) {
        await Future<void>.delayed(const Duration(milliseconds: 10));
      }
    });
    await tester.pump();
    expect(sent.length, before + 1);
    expect(sent.last, isA<Uint8List>());
  }

  void tracking() => socket.reply({
    'type': 'tracking',
    'timestamp_ms': DateTime.now().millisecondsSinceEpoch,
    'quality': true,
    'landmarks': [],
    'liveness_passed': true,
    'message': 'Tracking is clear',
  });

  testWidgets('a five-second frame reply recovers without ending the take', (
    tester,
  ) async {
    await open(tester);
    await sendFrame(tester);
    await tester.pump(const Duration(seconds: 5));
    expect(camera.disposed, isFalse);
    expect(find.textContaining('Waiting for gesture tracking'), findsOneWidget);
    tracking();
    await tester.pump();
    expect(find.textContaining('Waiting for gesture tracking'), findsNothing);
    expect(find.text('Start take 1'), findsOneWidget);
    // A recovered response must cancel the old deadline.
    await tester.pump(const Duration(seconds: 10));
    expect(camera.disposed, isFalse);
    await tester.pumpWidget(const SizedBox());
    await tester.pump();
    expect(tester.takeException(), isNull);
  });

  testWidgets('a stalled frame stops safely at the deadline', (tester) async {
    await open(tester);
    await sendFrame(tester);
    await tester.pump(const Duration(seconds: 12));
    await tester.runAsync(() => Future<void>.delayed(Duration.zero));
    await tester.pump();
    expect(
      find.textContaining(
        'did not reply to gesture tracking within 12 seconds',
      ),
      findsOneWidget,
    );
    expect(camera.disposed, isTrue);
    expect(socket.output.closed, isTrue);
    expect(find.text('Back to my vault'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await tester.pump();
    expect(tester.takeException(), isNull);
  });

  testWidgets('a transient vision error clears when tracking recovers', (
    tester,
  ) async {
    await open(tester);
    socket.reply({
      'type': 'error',
      'code': 'vision_timeout',
      'retryable': true,
      'message': 'Gesture processing took too long.',
    });
    await tester.pump();
    expect(find.text('Gesture processing took too long.'), findsOneWidget);
    tracking();
    await tester.pump();
    expect(find.text('Gesture processing took too long.'), findsNothing);
    expect(camera.disposed, isFalse);
    await tester.pumpWidget(const SizedBox());
    await tester.pump();
  });

  testWidgets('starting a take tolerates a delayed command reply', (
    tester,
  ) async {
    await open(tester);
    tracking();
    await tester.pump();
    await tester.ensureVisible(find.text('Start take 1'));
    await tester.tap(find.text('Start take 1'));
    for (var i = 0; i < 3; i++) {
      await tester.pump(const Duration(seconds: 1));
    }
    expect(
      sent.whereType<String>().map((raw) => jsonDecode(raw)['type']),
      contains('begin'),
    );
    await tester.pump(const Duration(seconds: 5));
    expect(camera.disposed, isFalse);
    expect(
      find.textContaining('Waiting for the capture command'),
      findsOneWidget,
    );
    socket.reply({'type': 'capturing'});
    await tester.pump();
    expect(
      find.textContaining('Waiting for the capture command'),
      findsNothing,
    );
    expect(find.text('Capturing…'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await tester.pump();
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'an invalid tracking reply shows an error without an unhandled exception',
    (tester) async {
      await open(tester);
      socket.incoming.add('not json');
      await tester.pump();
      expect(find.textContaining('invalid tracking response'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      await tester.pump();
    },
  );
}
