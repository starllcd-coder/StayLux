import '../../../../core/network/api_client.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/storage/secure_storage_service.dart';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../models/notification_model.dart';

class NotificationApi {
  final ApiClient client;
  final SecureStorageService storage = SecureStorageService();

  NotificationApi(this.client);

  Future<void> ensureDeviceRegistered() async {
    var token = await storage.getString(AppConstants.pushDeviceTokenKey);
    if (token == null || token.trim().isEmpty) {
      token = "staylux-${kIsWeb ? "web" : "mobile"}-${DateTime.now().millisecondsSinceEpoch}";
      await storage.saveString(AppConstants.pushDeviceTokenKey, token);
    }
    await client.post(
      "/notifications/devices/register/",
      {
        "device_token": token,
        "platform": kIsWeb ? "web" : defaultTargetPlatform.name,
      },
    );
  }

  Future<List<AppNotificationModel>> getNotifications() async {
    try {
      final response = await client.get("/notifications/");
      final data = response.data;
      final List results;

      if (data is Map<String, dynamic>) {
        final raw = data["results"];
        results = raw is List ? raw : <dynamic>[];
      } else if (data is List) {
        results = data;
      } else {
        results = <dynamic>[];
      }

      await storage.saveString(AppConstants.cacheNotificationsKey, jsonEncode(results));
      return results
          .whereType<Map>()
          .map((item) => AppNotificationModel.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    } catch (_) {
      final raw = await storage.getString(AppConstants.cacheNotificationsKey);
      if (raw != null && raw.trim().isNotEmpty) {
        final decoded = jsonDecode(raw);
        if (decoded is List) {
          return decoded
              .whereType<Map>()
              .map((item) => AppNotificationModel.fromJson(Map<String, dynamic>.from(item)))
              .toList();
        }
      }
      rethrow;
    }
  }

  Future<void> markAsRead(int id) async {
    await client.post("/notifications/$id/read/", {});
  }
}
