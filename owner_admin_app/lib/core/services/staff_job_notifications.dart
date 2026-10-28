import 'package:flutter/foundation.dart';
import '../../data/datasources/api_client.dart';
import '../../data/repositories/token_storage.dart';

class StaffJobNotifications extends ChangeNotifier {
  static final instance = StaffJobNotifications();
  final ApiClient _api = ApiClient();
  List<Map<String, dynamic>> items = [];
  String? error;
  String? _userId;
  bool _loading = false;
  int get unreadCount => items.where((n) => n['is_read'] != true).length;

  Future<void> refresh() async {
    final userId = TokenStorage.currentUserId;
    if (TokenStorage.currentToken == null || userId == null) {
      items = [];
      _userId = null;
      error = null;
      notifyListeners();
      return;
    }
    if (_userId != userId) {
      items = [];
      _userId = userId;
      notifyListeners();
    }
    if (_loading || TokenStorage.currentBackendRole == 'owner') return;
    _loading = true;
    try {
      final result = await _api.getList('/api/staff-job-notifications/');
      if (TokenStorage.currentUserId != userId || TokenStorage.currentToken == null) return;
      items = result.map((n) => Map<String, dynamic>.from(n as Map)).toList();
      error = null;
    } catch (_) {
      error = 'Could not load job notifications. Please retry.';
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> markRead(int id) async {
    await _api.postJson('/api/staff-job-notifications/$id/read/', body: {}, authenticated: true);
    await refresh();
  }
}
