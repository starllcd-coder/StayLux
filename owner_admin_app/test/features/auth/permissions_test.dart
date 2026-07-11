import 'package:flutter_test/flutter_test.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_access_controller.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_route_access_controller.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_session_controller.dart';
import 'package:owner_admin_app/features/auth/controllers/backend_permission_matrix.dart';

class _FakeSessionController extends AdminSessionController {
  final String? role;
  final String? backendRole;

  _FakeSessionController({
    this.role,
    this.backendRole,
  });

  @override
  String? getCurrentRole() => role;

  @override
  String? getCurrentBackendRole() => backendRole;
}

void main() {
  group('BackendPermissionMatrix', () {
    test('owner_admin has full access', () {
      const matrix = BackendPermissionMatrix('owner_admin');
      expect(matrix.canViewRevenue(), isTrue);
      expect(matrix.canManageStaff(), isTrue);
      expect(matrix.canManageSecurity(), isTrue);
      expect(matrix.canManageMaintenance(), isTrue);
      expect(matrix.canManageHousekeeping(), isTrue);
      expect(matrix.canViewReservations(), isTrue);
      expect(matrix.canViewDashboard(), isTrue);
    });

    test('reception has limited access', () {
      const matrix = BackendPermissionMatrix('reception');
      expect(matrix.canViewRevenue(), isFalse);
      expect(matrix.canManageStaff(), isFalse);
      expect(matrix.canManageSecurity(), isFalse);
      expect(matrix.canManageMaintenance(), isFalse);
      expect(matrix.canManageHousekeeping(), isFalse);
      expect(matrix.canViewReservations(), isTrue);
      expect(matrix.canViewDashboard(), isTrue);
    });
  });

  group('AdminAccessController', () {
    test('uses backend role matrix when backend role exists', () {
      final controller = AdminAccessController(
        sessionController: _FakeSessionController(
          role: 'staff',
          backendRole: 'manager',
        ),
      );

      expect(controller.canViewRevenue(), isTrue);
      expect(controller.canManageStaff(), isTrue);
      expect(controller.canManageSecurity(), isTrue);
      expect(controller.canManageHousekeeping(), isTrue);
      expect(controller.canManageMaintenance(), isTrue);
    });

    test('falls back to app role when backend role is missing', () {
      final controller = AdminAccessController(
        sessionController: _FakeSessionController(
          role: 'staff',
          backendRole: '',
        ),
      );

      expect(controller.canViewRevenue(), isFalse);
      expect(controller.canManageStaff(), isFalse);
      expect(controller.canManageSecurity(), isFalse);
      expect(controller.canManageHousekeeping(), isTrue);
      expect(controller.canManageMaintenance(), isTrue);
      expect(controller.canViewReservations(), isTrue);
    });
  });

  group('AdminRouteAccessController', () {
    test('manager backend role can access reports and notifications', () {
      final controller = AdminRouteAccessController(
        sessionController: _FakeSessionController(
          backendRole: 'manager',
        ),
      );

      expect(controller.canOpenRoute('/admin/reports'), isTrue);
      expect(controller.canOpenRoute('/admin/notifications'), isTrue);
      expect(controller.canOpenRoute('/admin/staff'), isTrue);
    });

    test('housekeeping backend role cannot access maintenance/staff', () {
      final controller = AdminRouteAccessController(
        sessionController: _FakeSessionController(
          backendRole: 'housekeeping',
        ),
      );

      expect(controller.canOpenRoute('/admin/housekeeping'), isTrue);
      expect(controller.canOpenRoute('/admin/reservations'), isTrue);
      expect(controller.canOpenRoute('/admin/dashboard'), isTrue);
      expect(controller.canOpenRoute('/admin/maintenance'), isFalse);
      expect(controller.canOpenRoute('/admin/staff'), isFalse);
      expect(controller.canOpenRoute('/admin/reports'), isFalse);
    });
  });
}
