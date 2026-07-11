import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_admin_app/core/realtime/realtime_service.dart';
import 'package:owner_admin_app/data/models/operations_models.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_access_controller.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_session_controller.dart';
import 'package:owner_admin_app/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:owner_admin_app/features/notifications/presentation/pages/notifications_page.dart';

class _FakeSession extends AdminSessionController {
  @override
  List<String> getPropertyIds() => ['1'];
}

class _FakeAccess extends AdminAccessController {
  _FakeAccess() : super(sessionController: _FakeSession());
}

class _FakeRealtime implements RealtimeService {
  final _controller = StreamController<DateTime>.broadcast();

  @override
  Stream<DateTime> get ticks => _controller.stream;

  @override
  void dispose() {
    _controller.close();
  }

  @override
  void start() {}

  @override
  void stop() {}
}

class _FakeDashboard extends AdminDashboardController {
  @override
  Future<NotificationSettingItem?> loadNotificationSetting({
    required String propertyId,
  }) async {
    return const NotificationSettingItem(
      id: 1,
      propertyProfile: '1',
      enableWhatsApp: true,
      defaultChannel: 'whatsapp',
      notes: '',
    );
  }

  @override
  Future<List<SecurityAlertItem>> loadSecurityAlerts({
    required String propertyId,
  }) async {
    return const [
      SecurityAlertItem(
        id: 1,
        title: 'alert_one',
        channel: 'whatsapp',
        status: 'pending',
        createdAt: '2026-04-04T10:00:00',
        isRead: false,
        content: 'msg',
        error: '',
      ),
    ];
  }
}

void main() {
  testWidgets('NotificationsPage renders center and preferences', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: NotificationsPage(
          accessController: _FakeAccess(),
          sessionController: _FakeSession(),
          dashboardController: _FakeDashboard(),
          realtimeService: _FakeRealtime(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Notification Preferences'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Notification Center'),
      220,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Notification Center'), findsOneWidget);
    expect(find.text('alert_one'), findsOneWidget);
  });
}
