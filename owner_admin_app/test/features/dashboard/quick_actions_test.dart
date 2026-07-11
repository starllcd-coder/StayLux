import 'package:flutter_test/flutter_test.dart';
import 'package:owner_admin_app/features/dashboard/controllers/admin_dashboard_controller.dart';

void main() {
  group('AdminDashboardController.visibleQuickActions', () {
    test('returns all actions for full-access user', () {
      final actions = AdminDashboardController.visibleQuickActions(
        canViewReservations: true,
        canManageHousekeeping: true,
        canManageMaintenance: true,
        canManageSecurity: true,
        canViewRevenue: true,
        canManageStaff: true,
      );

      final titles = actions.map((e) => e['title']).toList();
      expect(titles, containsAll(<String>[
        'Reservations',
        'Housekeeping',
        'Maintenance',
        'Security',
        'Notifications',
        'Reports',
        'Settings',
        'Staff',
      ]));
    });

    test('hides restricted modules for limited-access user', () {
      final actions = AdminDashboardController.visibleQuickActions(
        canViewReservations: true,
        canManageHousekeeping: true,
        canManageMaintenance: false,
        canManageSecurity: false,
        canViewRevenue: false,
        canManageStaff: false,
      );

      final titles = actions.map((e) => e['title']).toList();
      expect(titles, contains('Reservations'));
      expect(titles, contains('Housekeeping'));
      expect(titles, isNot(contains('Maintenance')));
      expect(titles, isNot(contains('Security')));
      expect(titles, isNot(contains('Reports')));
      expect(titles, isNot(contains('Staff')));
      expect(titles, contains('Notifications'));
      expect(titles, contains('Settings'));
    });
  });
}
