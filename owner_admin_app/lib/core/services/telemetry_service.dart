import 'dart:convert';
import 'dart:developer';

import 'package:flutter/foundation.dart';

class TelemetryService {
  TelemetryService._();

  static final TelemetryService instance = TelemetryService._();

  bool _initialized = false;

  void initialize() {
    if (_initialized) return;
    _initialized = true;
    trackEvent('telemetry_initialized');
  }

  void trackScreen(String screenName) {
    trackEvent('screen_view', properties: {'screen': screenName});
  }

  void trackEvent(String eventName, {Map<String, dynamic>? properties}) {
    final payload = {
      'type': 'event',
      'event': eventName,
      'properties': properties ?? const <String, dynamic>{},
      'ts': DateTime.now().toIso8601String(),
    };
    log(jsonEncode(payload), name: 'StayLuxTelemetry');
  }

  void reportError(
    Object error,
    StackTrace stackTrace, {
    String source = 'unknown',
    bool fatal = false,
  }) {
    final payload = {
      'type': 'error',
      'source': source,
      'fatal': fatal,
      'error': error.toString(),
      'stack': stackTrace.toString(),
      'ts': DateTime.now().toIso8601String(),
    };
    log(jsonEncode(payload), name: 'StayLuxTelemetry', level: fatal ? 1000 : 900);

    if (kDebugMode) {
      debugPrint('Telemetry error [$source]: $error');
    }
  }
}
