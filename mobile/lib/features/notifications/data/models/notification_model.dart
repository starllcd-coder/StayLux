import '../../domain/entities/notification.dart';

class AppNotificationModel extends AppNotification {
  AppNotificationModel({
    required super.id,
    required super.title,
    required super.message,
    required super.isRead,
    required super.createdAt,
  });

  factory AppNotificationModel.fromJson(Map<String, dynamic> json) {
    return AppNotificationModel(
      id: json["id"] ?? 0,
      title: (json["title"] ?? "").toString(),
      message: (json["message"] ?? "").toString(),
      isRead: json["is_read"] ?? false,
      createdAt: (json["created_at"] ?? "").toString(),
    );
  }
}