import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_auth_controller.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_session_controller.dart';
import 'package:owner_admin_app/features/settings/presentation/pages/admin_settings_page.dart';

class _FakeSession extends AdminSessionController {
  @override
  String? getCurrentUserName() => 'Test User';

  @override
  String? getCurrentEmail() => 'test@staylux.com';

  @override
  String? getCurrentRole() => 'manager';

  @override
  String? getCurrentBackendRole() => 'manager';

  @override
  String? getCurrentUserId() => '42';

  @override
  List<String> getPropertyIds() => ['1', '2'];
}

class _FakeAuth extends AdminAuthController {
  @override
  Future<void> logout() async {}
}

void main() {
  testWidgets('AdminSettingsPage shows profile info', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: AdminSettingsPage(
          sessionController: _FakeSession(),
          authController: _FakeAuth(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Profile'), findsOneWidget);
    expect(find.text('Test User'), findsOneWidget);
    expect(find.text('test@staylux.com'), findsOneWidget);
    expect(find.text('MANAGER'), findsOneWidget);
  });
}
