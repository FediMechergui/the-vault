import 'dart:async';
import 'dart:convert';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'api.dart';
import 'design.dart';
import 'frame_encoder.dart';
import 'response_deadline.dart';
import 'screens.dart' show demoMode;

class CaptureScreen extends StatefulWidget {
  final VaultApi api;
  final Map<String, dynamic> session;
  final bool enrollment;
  const CaptureScreen({
    super.key,
    required this.api,
    required this.session,
    required this.enrollment,
  });
  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen>
    with WidgetsBindingObserver {
  CameraController? camera;
  WebSocketChannel? socket;
  StreamSubscription? subscription;
  Timer? frameTimer, captureTimer;
  late final ResponseDeadline frameDeadline, commandDeadline;
  Future<void>? cameraShutdown;
  late Map<String, dynamic> challenge;
  Map<String, dynamic> tracking = {};
  final List<Offset> trail = [];
  bool ready = false,
      sending = false,
      awaiting = false,
      capturing = false,
      deciding = false,
      live = false,
      drawn = false,
      stopped = false;
  int frameId = 0, lastSent = 0, countdown = 0, completed = 0, received = 0;
  final Stopwatch fpsWatch = Stopwatch()..start();
  final Stopwatch captureWatch = Stopwatch();
  double progress = 0, roundTrip = 0;
  String? error;
  String? streamNotice;
  bool transientTrackingError = false;
  String? lastScore;
  String get layer => challenge['layer'] as String;
  String get sid => widget.session['session_id'];
  String get secret => widget.session['session_token'];
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    challenge = Map<String, dynamic>.from(widget.session['challenge']);
    live = challenge['liveness'] == null;
    frameDeadline = _deadline('gesture tracking');
    commandDeadline = _deadline('the capture command');
    _initialize();
  }

  ResponseDeadline _deadline(String operation) => ResponseDeadline(
    onSlow: () {
      if (mounted && !stopped) {
        setState(
          () => streamNotice = 'Waiting for $operation… Keep the app open.',
        );
      }
    },
    onExpired: () => _fail(
      'Your computer did not reply to $operation within 12 seconds. '
      'Go back and start a fresh take. Check the PC terminal if it happens again.',
    ),
  );

  Future<void> _initialize() async {
    try {
      // A server enrollment/auth session exists only after the account consent gate.
      final cameras = await availableCameras();
      if (!mounted || stopped) return;
      if (cameras.isEmpty) {
        throw VaultException(
          'No camera found. Connect a camera or use your Android phone.',
        );
      }
      final selected = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        selected,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: defaultTargetPlatform == TargetPlatform.iOS
            ? ImageFormatGroup.bgra8888
            : ImageFormatGroup.yuv420,
      );
      camera = controller;
      await controller.initialize();
      if (!mounted || stopped) {
        await _stopCamera();
        return;
      }
      if (!kIsWeb) {
        await controller.lockCaptureOrientation(DeviceOrientation.portraitUp);
      }
      socket = await widget.api.stream(sid, secret);
      if (!mounted || stopped) {
        await socket?.sink.close();
        return;
      }
      commandDeadline.start();
      subscription = socket!.stream.listen(
        _message,
        onError: (Object e) => _fail(friendlyError(e)),
        onDone: () {
          if (!stopped) {
            final code = socket?.closeCode;
            _fail(
              code == 1008
                  ? 'This capture session expired or was reset on the PC. Go back and start a fresh take.'
                  : 'The camera stream closed${code == null ? '' : ' (code $code)'}. Go back and start a fresh take.',
            );
          }
        },
      );
      if (kIsWeb) {
        frameTimer = Timer.periodic(
          const Duration(milliseconds: 67),
          (_) => _webFrame(),
        );
      } else {
        await controller.startImageStream(_nativeFrame);
      }
      if (!mounted || stopped) return;
      setState(() {});
    } on CameraException catch (e) {
      _fail(
        e.code.contains('Access')
            ? 'Camera access is needed for this challenge. Enable it in your device settings, then return.'
            : 'Could not start the camera: ${e.description}',
      );
    } catch (e) {
      _fail(friendlyError(e));
    }
  }

  bool get canSend =>
      mounted &&
      ready &&
      !stopped &&
      !sending &&
      !awaiting &&
      !deciding &&
      DateTime.now().millisecondsSinceEpoch - lastSent >= 66;
  Future<void> _nativeFrame(CameraImage image) async {
    if (!canSend) return;
    sending = true;
    try {
      final jpeg = await compute(encodeFrame, {
        'width': image.width,
        'height': image.height,
        'planes': image.planes.map((p) => Uint8List.fromList(p.bytes)).toList(),
        'strides': image.planes.map((p) => p.bytesPerRow).toList(),
        'pixels': image.planes.map((p) => p.bytesPerPixel ?? 1).toList(),
        'rotation': defaultTargetPlatform == TargetPlatform.android
            ? camera!.description.sensorOrientation
            : 0,
      });
      _send(jpeg);
    } catch (_) {
      _fail(
        'This camera frame format is not supported. Try another camera device.',
      );
    } finally {
      sending = false;
    }
  }

  Future<void> _webFrame() async {
    if (!canSend || camera?.value.isInitialized != true) return;
    sending = true;
    try {
      final file = await camera!.takePicture();
      _send(await file.readAsBytes());
    } catch (_) {
      _fail(
        'Browser camera capture failed. Check camera permission and use HTTPS or localhost.',
      );
    } finally {
      sending = false;
    }
  }

  void _send(Uint8List jpeg) {
    if (!mounted || stopped || socket == null) return;
    lastSent = DateTime.now().millisecondsSinceEpoch;
    final bytes = Uint8List(12 + jpeg.length);
    final header = ByteData.sublistView(bytes);
    header.setUint32(0, frameId++);
    header.setUint64(4, lastSent);
    bytes.setRange(12, bytes.length, jpeg);
    awaiting = true;
    frameDeadline.start();
    socket!.sink.add(bytes);
  }

  void _message(dynamic raw) {
    if (!mounted || stopped) return;
    try {
      _handleMessage(raw);
    } catch (_) {
      _fail(
        'The PC sent an invalid tracking response. Update the server and start a fresh take.',
      );
    }
  }

  void _handleMessage(dynamic raw) {
    final message = jsonDecode(raw as String) as Map<String, dynamic>;
    switch (message['type']) {
      case 'ready':
        commandDeadline.cancel();
        setState(() => ready = true);
        break;
      case 'tracking':
        frameDeadline.cancel();
        streamNotice = null;
        if (transientTrackingError) error = null;
        transientTrackingError = false;
        awaiting = false;
        received++;
        roundTrip =
            (DateTime.now().millisecondsSinceEpoch -
                    (message['timestamp_ms'] as num))
                .toDouble();
        tracking = message;
        live =
            message['liveness_passed'] == true || challenge['liveness'] == null;
        if (layer == 'hand' && capturing && message['drawing'] == true) {
          if (!drawn) {
            drawn = true;
            captureWatch.reset();
          }
          final points = message['landmarks'] as List;
          if (points.length > 8 && message['quality'] == true) {
            trail.add(
              Offset(
                (points[8][0] as num).toDouble(),
                (points[8][1] as num).toDouble(),
              ),
            );
            if (trail.length > 180) trail.removeAt(0);
          }
        }
        if (capturing && message['trace_done'] == true) _finish();
        setState(() {});
        break;
      case 'capturing':
        commandDeadline.cancel();
        streamNotice = null;
        capturing = true;
        deciding = false;
        drawn = false;
        captureWatch
          ..reset()
          ..start();
        captureTimer?.cancel();
        captureTimer = Timer.periodic(const Duration(milliseconds: 50), (_) {
          if (!mounted || !capturing) return;
          final duration = (challenge['duration_ms'] as num).toDouble();
          setState(
            () => progress = (captureWatch.elapsedMilliseconds / duration)
                .clamp(0, 1),
          );
          if (layer == 'hand' && !drawn) {
            if (captureWatch.elapsedMilliseconds > 11000) _finish();
          } else if (captureWatch.elapsedMilliseconds >= duration) {
            _finish();
          }
        });
        setState(() {});
        break;
      case 'captured':
        commandDeadline.cancel();
        streamNotice = null;
        capturing = false;
        deciding = false;
        completed = message['completed'];
        captureTimer?.cancel();
        if (message['ready_to_commit'] == true) {
          _decide();
        } else {
          setState(() {
            progress = 0;
            trail.clear();
          });
          HapticFeedback.lightImpact();
        }
        break;
      case 'quality_error':
        commandDeadline.cancel();
        streamNotice = null;
        transientTrackingError = false;
        captureTimer?.cancel();
        captureWatch.stop();
        setState(() {
          capturing = false;
          deciding = false;
          countdown = 0;
          error = message['message'];
          progress = 0;
        });
        break;
      case 'error':
        frameDeadline.cancel();
        commandDeadline.cancel();
        streamNotice = null;
        transientTrackingError =
            message['retryable'] == true ||
            message['message'] == 'Vision service unavailable';
        awaiting = false;
        setState(() {
          error = message['message'] == 'Vision service unavailable'
              ? 'Gesture tracking on the PC is temporarily unavailable. Retrying the next frame…'
              : message['message'];
          deciding = false;
        });
        break;
      case 'dropped':
        frameDeadline.cancel();
        awaiting = false;
        break;
    }
  }

  Future<void> _countdown() async {
    if (!ready || capturing || deciding || countdown > 0 || !live) return;
    setState(() {
      error = null;
      trail.clear();
      progress = 0;
    });
    for (var i = 3; i > 0; i--) {
      if (!mounted || stopped) return;
      setState(() => countdown = i);
      HapticFeedback.selectionClick();
      await Future<void>.delayed(const Duration(seconds: 1));
    }
    if (!mounted || stopped) return;
    setState(() {
      countdown = 0;
      deciding = true;
    });
    commandDeadline.start();
    socket!.sink.add(jsonEncode({'type': 'begin'}));
  }

  void _finish() {
    if (!capturing) return;
    captureTimer?.cancel();
    captureWatch.stop();
    capturing = false;
    deciding = true;
    commandDeadline.start();
    socket?.sink.add(jsonEncode({'type': 'finish'}));
    if (mounted) setState(() {});
  }

  Future<void> _decide() async {
    setState(() => deciding = true);
    try {
      if (widget.enrollment) {
        final result = await widget.api.request(
          'POST',
          '/api/v1/enroll/$layer/commit',
          data: {'session_id': sid},
        );
        stopped = true;
        await _stopCamera();
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${layer.toUpperCase()} recorded · ${result['engine']}',
            ),
          ),
        );
        Navigator.of(context).pop(true);
      } else {
        final result = await widget.api.request(
          'POST',
          '/api/v1/auth/$sid/next',
          sessionToken: secret,
        );
        final score = (result['result']['score'] as num) * 100;
        lastScore =
            '${score.toStringAsFixed(1)}% · ${result['result']['engine']}';
        if (result['status'] == 'unlocked') {
          widget.api.accessToken = result['access_token'];
          stopped = true;
          await _stopCamera();
          if (mounted) Navigator.of(context).pop(true);
        } else if (result['status'] == 'failed') {
          stopped = true;
          await _stopCamera();
          if (mounted) {
            setState(() {
              error =
                  (result['locked_until'] as num) >
                      DateTime.now().millisecondsSinceEpoch / 1000
                  ? 'Three unsuccessful attempts. Your vault is locked for five minutes.'
                  : 'That wasn’t your enrolled gesture. Go back and try again.';
              deciding = false;
            });
          }
        } else {
          HapticFeedback.mediumImpact();
          setState(() {
            challenge = Map<String, dynamic>.from(result['challenge']);
            live = challenge['liveness'] == null;
            completed = 0;
            progress = 0;
            trail.clear();
            deciding = false;
            tracking = {};
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          error = friendlyError(e);
          deciding = false;
        });
      }
    }
  }

  void _fail(String message) {
    if (!mounted || stopped) return;
    stopped = true;
    _stopCamera();
    setState(() {
      error = message;
      ready = false;
      capturing = false;
      deciding = false;
    });
  }

  Future<void> _stopCamera() => cameraShutdown ??= _releaseCamera();

  Future<void> _releaseCamera() async {
    frameTimer?.cancel();
    captureTimer?.cancel();
    frameDeadline.cancel();
    commandDeadline.cancel();
    final controller = camera;
    camera = null;
    if (controller?.value.isStreamingImages == true) {
      try {
        await controller!.stopImageStream();
      } catch (_) {}
    }
    // A camera-plugin disposal error must not prevent socket cleanup or become
    // an unhandled asynchronous exception while leaving the capture screen.
    try {
      await controller?.dispose();
    } catch (_) {}
    // Start both operations: stream cancellation can wait for its transport.
    // It must not prevent us from initiating that transport's close.
    final closing = () async {
      try {
        await socket?.sink.close();
      } catch (_) {}
    }();
    try {
      await subscription?.cancel();
    } catch (_) {}
    await closing;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused) {
      _fail('Capture paused for your privacy. Go back to start again.');
    }
  }

  @override
  void dispose() {
    stopped = true;
    WidgetsBinding.instance.removeObserver(this);
    _stopCamera();
    super.dispose();
  }

  String get instruction {
    if (!live) {
      return {
            'blink_twice': 'Blink twice, then open your eyes.',
            'turn_left': 'Face forward, then turn your head left.',
            'turn_right': 'Face forward, then turn your head right.',
          }[challenge['liveness']] ??
          'Follow the liveness challenge.';
    }
    return {
      'face': 'Repeat your two secret expressions in the same order.',
      'body': 'Set your phone down. Repeat your 3–6 second dance.',
      'hand': 'Open your hand. Pinch, release and draw. Pinch again to finish.',
    }[layer]!;
  }

  @override
  Widget build(BuildContext context) {
    final landmarks = (tracking['landmarks'] as List? ?? []);
    final quality = tracking['quality'] == true;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 10, 24, 8),
                  child: Row(
                    children: [
                      IconButton(
                        tooltip: 'Cancel capture',
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const Text('×', style: TextStyle(fontSize: 32)),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Eyebrow(
                          widget.enrollment
                              ? 'Enrollment / $layer'
                              : 'Challenge ${challenge['step']} of ${challenge['total']}',
                        ),
                      ),
                      if (demoMode) const Eyebrow('Live', color: lime),
                    ],
                  ),
                ),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(24, 10, 24, 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          {
                            'face': 'A familiar face.',
                            'body': 'Make your move.',
                            'hand': 'Leave your mark.',
                          }[layer]!,
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          instruction,
                          style: const TextStyle(
                            fontSize: 13,
                            color: muted,
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(height: 20),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(28),
                          child: AspectRatio(
                            aspectRatio: kIsWeb ? 4 / 3 : 3 / 4,
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                Container(color: surface),
                                if (camera?.value.isInitialized == true)
                                  CameraPreview(camera!),
                                CustomPaint(
                                  painter: TrackingPainter(
                                    layer: layer,
                                    points: landmarks,
                                    trail: trail,
                                    quality: quality,
                                    demo: demoMode,
                                    mirror:
                                        camera?.description.lensDirection ==
                                        CameraLensDirection.front,
                                  ),
                                ),
                                Positioned(
                                  top: 16,
                                  left: 16,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 12,
                                      vertical: 7,
                                    ),
                                    decoration: BoxDecoration(
                                      color: ink.withValues(alpha: 0.85),
                                      borderRadius: BorderRadius.circular(20),
                                    ),
                                    child: Eyebrow(
                                      capturing
                                          ? '● Recording'
                                          : !live
                                          ? 'Liveness check'
                                          : '● Live preview',
                                      color: capturing ? lime : paper,
                                    ),
                                  ),
                                ),
                                if (countdown > 0)
                                  Center(
                                    child: Text(
                                      '$countdown',
                                      style: const TextStyle(
                                        fontSize: 100,
                                        fontWeight: FontWeight.w500,
                                        color: lime,
                                      ),
                                    ),
                                  ),
                                Positioned(
                                  bottom: 16,
                                  left: 16,
                                  right: 16,
                                  child: Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: ink.withValues(alpha: 0.85),
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                    child: Row(
                                      children: [
                                        Container(
                                          width: 6,
                                          height: 6,
                                          decoration: BoxDecoration(
                                            shape: BoxShape.circle,
                                            color: quality ? lime : muted,
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            streamNotice ??
                                                tracking['message'] ??
                                                'Waiting for camera tracking…',
                                            style: const TextStyle(
                                              fontSize: 11,
                                            ),
                                          ),
                                        ),
                                        if (tracking['gesture'] != null)
                                          Text(
                                            tracking['gesture'],
                                            style: const TextStyle(
                                              fontSize: 10,
                                              color: lime,
                                            ),
                                          ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 18),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(5),
                          child: LinearProgressIndicator(
                            value: progress,
                            minHeight: 3,
                            color: lime,
                            backgroundColor: line,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Eyebrow(
                              widget.enrollment
                                  ? 'Take ${(completed + 1).clamp(1, challenge['repetitions'])} / ${challenge['repetitions']}'
                                  : 'Encrypted session',
                            ),
                            Eyebrow(
                              layer == 'hand'
                                  ? (tracking['drawing'] == true
                                        ? 'Drawing…'
                                        : 'Pinch to trace')
                                  : '${(challenge['duration_ms'] / 1000).toStringAsFixed(1)} seconds',
                            ),
                          ],
                        ),
                        if (demoMode)
                          Padding(
                            padding: const EdgeInsets.only(top: 14),
                            child: Text(
                              '${roundTrip.toStringAsFixed(0)} ms round trip  ·  ${(received / (fpsWatch.elapsedMilliseconds / 1000)).toStringAsFixed(1)} FPS\n${tracking['samples'] ?? 0} samples  ·  ${landmarks.length} landmarks${lastScore != null ? '\nPrevious score: $lastScore' : ''}',
                              style: const TextStyle(
                                fontSize: 11,
                                color: lime,
                                height: 1.7,
                              ),
                            ),
                          ),
                        if (error != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 18),
                            child: Text(
                              error!,
                              style: const TextStyle(
                                color: Color(0xFFF7BA96),
                                fontSize: 13,
                              ),
                            ),
                          ),
                        const SizedBox(height: 24),
                        if (stopped)
                          VaultButton(
                            'Back to my vault',
                            onPressed: () => Navigator.of(context).pop(),
                          )
                        else
                          VaultButton(
                            deciding
                                ? 'Comparing your movement…'
                                : capturing
                                ? 'Capturing…'
                                : countdown > 0
                                ? 'Get ready…'
                                : !live
                                ? 'Complete the liveness check'
                                : 'Start ${widget.enrollment ? 'take ${completed + 1}' : 'challenge'}',
                            onPressed:
                                ready &&
                                    live &&
                                    !capturing &&
                                    countdown == 0 &&
                                    quality
                                ? _countdown
                                : null,
                            busy: deciding,
                          ),
                        if (error != null &&
                            !stopped &&
                            completed >=
                                (widget.enrollment
                                    ? challenge['repetitions']
                                    : 1))
                          TextButton(
                            onPressed: _decide,
                            child: const Text('Retry scoring'),
                          ),
                        const SizedBox(height: 12),
                        const Center(
                          child: Text(
                            'Images disappear. Only your pattern remains.',
                            style: TextStyle(color: muted, fontSize: 10),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class TrackingPainter extends CustomPainter {
  final String layer;
  final List points;
  final List<Offset> trail;
  final bool quality, demo, mirror;
  TrackingPainter({
    required this.layer,
    required this.points,
    required this.trail,
    required this.quality,
    required this.demo,
    required this.mirror,
  });
  static const handEdges = [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 4],
    [0, 5],
    [5, 6],
    [6, 7],
    [7, 8],
    [5, 9],
    [9, 10],
    [10, 11],
    [11, 12],
    [9, 13],
    [13, 14],
    [14, 15],
    [15, 16],
    [13, 17],
    [17, 18],
    [18, 19],
    [19, 20],
    [17, 0],
  ];
  static const bodyEdges = [
    [11, 12],
    [11, 13],
    [13, 15],
    [12, 14],
    [14, 16],
    [11, 23],
    [12, 24],
    [23, 24],
    [23, 25],
    [25, 27],
    [24, 26],
    [26, 28],
    [27, 31],
    [28, 32],
  ];
  @override
  void paint(Canvas canvas, Size size) {
    Offset point(dynamic p) => Offset(
      (mirror ? 1 - (p[0] as num) : (p[0] as num)) * size.width,
      (p[1] as num) * size.height,
    );
    final paint = Paint()
      ..color = quality ? lime : muted
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    if (layer == 'face') {
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(size.width / 2, size.height * 0.46),
          width: size.width * 0.67,
          height: size.height * 0.65,
        ),
        paint,
      );
    }
    if (layer == 'body' && points.isEmpty) {
      final ghost = Paint()
        ..color = lime.withValues(alpha: 0.22)
        ..strokeWidth = 3
        ..style = PaintingStyle.stroke;
      canvas.drawCircle(
        Offset(size.width / 2, size.height * 0.2),
        size.width * 0.07,
        ghost,
      );
      canvas.drawPath(
        Path()
          ..moveTo(size.width * 0.25, size.height * 0.44)
          ..lineTo(size.width * 0.5, size.height * 0.3)
          ..lineTo(size.width * 0.75, size.height * 0.44)
          ..moveTo(size.width * 0.5, size.height * 0.3)
          ..lineTo(size.width * 0.5, size.height * 0.58)
          ..lineTo(size.width * 0.35, size.height * 0.82)
          ..moveTo(size.width * 0.5, size.height * 0.58)
          ..lineTo(size.width * 0.65, size.height * 0.82),
        ghost,
      );
    }
    if (demo || layer != 'face') {
      final edges = layer == 'hand'
          ? handEdges
          : layer == 'body'
          ? bodyEdges
          : <List<int>>[];
      for (final edge in edges) {
        if (points.length > edge[1]) {
          canvas.drawLine(
            point(points[edge[0]]),
            point(points[edge[1]]),
            paint,
          );
        }
      }
      for (final p in points) {
        canvas.drawCircle(
          point(p),
          layer == 'face' ? 0.9 : 2,
          Paint()..color = lime.withValues(alpha: quality ? 0.8 : 0.3),
        );
      }
    }
    if (trail.length > 1) {
      final path = Path();
      for (var i = 0; i < trail.length; i++) {
        final p = Offset(
          (mirror ? 1 - trail[i].dx : trail[i].dx) * size.width,
          trail[i].dy * size.height,
        );
        if (i == 0) {
          path.moveTo(p.dx, p.dy);
        } else {
          path.lineTo(p.dx, p.dy);
        }
      }
      canvas.drawPath(
        path,
        Paint()
          ..color = lime.withValues(alpha: 0.2)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 9
          ..strokeCap = StrokeCap.round,
      );
      canvas.drawPath(
        path,
        Paint()
          ..color = lime
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.5
          ..strokeCap = StrokeCap.round,
      );
    }
  }

  @override
  bool shouldRepaint(covariant TrackingPainter old) => true;
}
