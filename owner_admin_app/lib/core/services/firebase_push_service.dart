import 'dart:async';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import '../config/firebase_push_config.dart';
import '../../data/datasources/api_client.dart';
import '../../data/repositories/token_storage.dart';
import 'staff_job_notifications.dart';

@pragma('vm:entry-point')
Future<void> staffPushBackgroundHandler(RemoteMessage message) async {
  if (!FirebasePushConfig.enabled || !FirebasePushConfig.configured) return;
  if (Firebase.apps.isEmpty) await Firebase.initializeApp(options: FirebasePushConfig.options);
  // FCM notification payloads are displayed by Android/iOS in the background.
  // Do not access authenticated user data from the background isolate.
}

class FirebasePushService {
  static final instance = FirebasePushService();
  final _api = ApiClient();
  bool _ready = false;
  int _sessionEpoch = 0;
  bool _busy = false;
  bool _pendingOpen = false;
  bool _permissionRequested = false;
  String? _registeredUser;
  String? _registeredToken;
  VoidCallback? onOpenInbox;

  bool get _supported => !kIsWeb && (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS);
  String get _platform => defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android';

  Future<void> initialize() async {
    if (!FirebasePushConfig.enabled || !FirebasePushConfig.configured || !_supported) return;
    try {
      await Firebase.initializeApp(options: FirebasePushConfig.options);
      FirebaseMessaging.onBackgroundMessage(staffPushBackgroundHandler);
      FirebaseMessaging.onMessage.listen((_) => StaffJobNotifications.instance.refresh());
      FirebaseMessaging.onMessageOpenedApp.listen(_openMessage);
      FirebaseMessaging.instance.onTokenRefresh.listen((_) {
        _registeredToken = null;
        syncSession();
      });
      final initial = await FirebaseMessaging.instance.getInitialMessage();
      if (initial?.data['type'] == 'staff_job') _pendingOpen = true;
      _ready = true;
    } catch (_) {
      // Missing platform configuration must not prevent normal login or jobs.
      debugPrint('Firebase push unavailable; in-app job notifications remain enabled.');
    }
  }

  void _openMessage(RemoteMessage message) {
    if (message.data['type'] != 'staff_job') return;
    _pendingOpen = true;
    syncSession();
  }

  Future<void> syncSession() async {
    if (!_ready || _busy) return;
    final userId = TokenStorage.currentUserId;
    if (userId == null || TokenStorage.currentToken == null || TokenStorage.currentBackendRole == 'owner') return;
    _busy = true;
    final epoch = _sessionEpoch;
    try {
      if (_pendingOpen && onOpenInbox != null) {
        _pendingOpen = false;
        onOpenInbox!();
      }
      var permission = await FirebaseMessaging.instance.getNotificationSettings();
      if (permission.authorizationStatus == AuthorizationStatus.notDetermined && !_permissionRequested) {
        _permissionRequested = true;
        permission = await FirebaseMessaging.instance.requestPermission(alert: true, badge: true, sound: true);
      }
      if (permission.authorizationStatus == AuthorizationStatus.denied) {
        if (_registeredToken != null) await unregister();
        return;
      }
      if (defaultTargetPlatform == TargetPlatform.iOS && await FirebaseMessaging.instance.getAPNSToken() == null) return;
      if (epoch != _sessionEpoch || TokenStorage.currentUserId != userId || TokenStorage.currentToken == null) return;
      await FirebaseMessaging.instance.setAutoInitEnabled(true);
      final token = await FirebaseMessaging.instance.getToken();
      if (token == null || epoch != _sessionEpoch || TokenStorage.currentUserId != userId || TokenStorage.currentToken == null) return;
      if (_registeredUser == userId && _registeredToken == token) return;
      await _api.postJson('/api/staff-push-devices/', authenticated: true, body: {'token': token, 'platform': _platform});
      if (epoch != _sessionEpoch || TokenStorage.currentUserId != userId || TokenStorage.currentToken == null) {
        await FirebaseMessaging.instance.deleteToken();
        return;
      }
      _registeredUser = userId;
      _registeredToken = token;
    } catch (_) {
      // Retry on the next foreground poll; never print device tokens.
      debugPrint('Push registration deferred; will retry while app is open.');
    } finally {
      _busy = false;
    }
  }

  Future<void> unregister() async {
    _sessionEpoch++;
    if (!_ready) return;
    try {
      final token = _registeredToken ?? await FirebaseMessaging.instance.getToken();
      if (token != null && TokenStorage.currentToken != null) {
        await _api.postJson('/api/staff-push-devices/unregister/', authenticated: true,
          body: {'token': token, 'platform': _platform}).timeout(const Duration(seconds: 5));
      }
    } catch (_) {
      // Deleting the provider token also prevents future delivery to this token.
    } finally {
      try {
        await FirebaseMessaging.instance.setAutoInitEnabled(false);
        await FirebaseMessaging.instance.deleteToken();
      } catch (_) {}
      _registeredToken = null;
      _registeredUser = null;
      _pendingOpen = false;
    }
  }
}
