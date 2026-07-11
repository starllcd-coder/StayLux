import 'package:flutter/foundation.dart';

class AppConfig {
  static const String _desktopDefaultApiBaseUrl = 'http://localhost:8000';
  static const String _androidDefaultApiBaseUrl = 'http://10.0.2.2:8000';
  static const String _iosDefaultApiBaseUrl = 'http://localhost:8000';
  static const String _fallbackMobileApiBaseUrl = 'http://192.168.1.10:8000';
  static const String supportEmail = 'support@deedarian.com';
  static const String supportWhatsApp = '+971500000000';

  static const String _apiBaseUrlFromEnv = String.fromEnvironment(
    'STAYLUX_API_BASE_URL',
    defaultValue: '',
  );

  static const String _mobileApiBaseUrlFromEnv = String.fromEnvironment(
    'STAYLUX_API_BASE_URL_MOBILE',
    defaultValue: '',
  );

  static String get apiBaseUrl {
    final global = _normalize(_apiBaseUrlFromEnv);
    if (global.isNotEmpty) return global;

    if (defaultTargetPlatform == TargetPlatform.android ||
        defaultTargetPlatform == TargetPlatform.iOS) {
      final mobile = _normalize(_mobileApiBaseUrlFromEnv);
      if (mobile.isNotEmpty) return mobile;

      if (defaultTargetPlatform == TargetPlatform.android) {
        return _androidDefaultApiBaseUrl;
      }
      return _iosDefaultApiBaseUrl;
    }

    if (kIsWeb) return _desktopDefaultApiBaseUrl;

    return _desktopDefaultApiBaseUrl;
  }

  static String get mobileOverrideHint => _fallbackMobileApiBaseUrl;

  static String _normalize(String raw) {
    final trimmed = raw.trim();
    if (trimmed.isEmpty) return '';
    if (trimmed.endsWith('/')) {
      return trimmed.substring(0, trimmed.length - 1);
    }
    return trimmed;
  }
}
