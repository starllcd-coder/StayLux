import '../../domain/entities/notification.dart';
import '../../domain/repositories/notification_repository.dart';
import '../datasources/notification_api.dart';

class NotificationRepositoryImpl implements NotificationRepository {
  final NotificationApi api;

  NotificationRepositoryImpl(this.api);

  @override
  Future<List<AppNotification>> getNotifications() {
    return api.getNotifications();
  }

  @override
  Future<void> markAsRead(int id) {
    return api.markAsRead(id);
  }
}