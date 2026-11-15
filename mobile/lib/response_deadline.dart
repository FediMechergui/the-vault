import 'dart:async';

/// A slow reply gets feedback before a bounded wait ends the capture.
class ResponseDeadline {
  final void Function() onSlow;
  final void Function() onExpired;
  Timer? _slow, _expired;

  ResponseDeadline({required this.onSlow, required this.onExpired});

  void start() {
    cancel();
    _slow = Timer(const Duration(seconds: 4), onSlow);
    _expired = Timer(const Duration(seconds: 12), onExpired);
  }

  void cancel() {
    _slow?.cancel();
    _expired?.cancel();
  }
}
