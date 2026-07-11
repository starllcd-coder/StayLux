import 'dart:async';

abstract class RealtimeService {
  Stream<DateTime> get ticks;
  void start();
  void stop();
  void dispose();
}

class PollingRealtimeService implements RealtimeService {
  final Duration interval;
  final StreamController<DateTime> _controller = StreamController<DateTime>.broadcast();
  Timer? _timer;

  PollingRealtimeService({this.interval = const Duration(seconds: 20)});

  @override
  Stream<DateTime> get ticks => _controller.stream;

  @override
  void start() {
    _timer?.cancel();
    _timer = Timer.periodic(interval, (_) {
      if (!_controller.isClosed) {
        _controller.add(DateTime.now());
      }
    });
  }

  @override
  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  @override
  void dispose() {
    stop();
    _controller.close();
  }
}
