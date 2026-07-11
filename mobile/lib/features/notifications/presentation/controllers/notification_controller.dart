import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

import '../../../../core/network/api_client.dart';
import '../../data/datasources/notification_api.dart';
import '../../data/repositories/notification_repository_impl.dart';
import '../../domain/entities/notification.dart';
import '../../domain/usecases/get_notifications.dart';

class NotificationState {
  final bool isLoading;
  final List<AppNotification> notifications;
  final String? error;

  const NotificationState({
    this.isLoading = false,
    this.notifications = const [],
    this.error,
  });

  NotificationState copyWith({
    bool? isLoading,
    List<AppNotification>? notifications,
    String? error,
    bool clearError = false,
  }) {
    return NotificationState(
      isLoading: isLoading ?? this.isLoading,
      notifications: notifications ?? this.notifications,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

final notificationControllerProvider =
    StateNotifierProvider<NotificationController, NotificationState>((ref) {
  return NotificationController();
});

class NotificationController extends StateNotifier<NotificationState> {
  NotificationController() : super(const NotificationState());

  final _repository =
      NotificationRepositoryImpl(NotificationApi(ApiClient()));

  Future<void> load() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _repository.api.ensureDeviceRegistered();
      final items = await GetNotifications(_repository).call();
      state = state.copyWith(
        isLoading: false,
        notifications: items,
        clearError: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _friendlyError(e),
      );
    }
  }

  Future<void> markAsRead(int id) async {
    state = state.copyWith(clearError: true);
    try {
      await _repository.markAsRead(id);
      await load();
    } catch (e) {
      state = state.copyWith(error: _friendlyError(e));
    }
  }

  int unreadCount() {
    return state.notifications.where((item) => !item.isRead).length;
  }

  String _friendlyError(Object error) {
    if (error is DioException) {
      if (error.response?.statusCode == 401) {
        return "Session expired. Please login again.";
      }
      final data = error.response?.data;
      if (data is Map<String, dynamic> && data.isNotEmpty) {
        final first = data.values.first;
        if (first is List && first.isNotEmpty) {
          return first.first.toString();
        }
        if (first != null) {
          return first.toString();
        }
      }
    }
    return error.toString();
  }
}
