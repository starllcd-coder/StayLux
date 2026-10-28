import '../../../data/models/role_permissions.dart';
import 'backend_permission_matrix.dart';
import 'admin_session_controller.dart';

class AdminRouteAccessController {
  final AdminSessionController _sessionController;

  AdminRouteAccessController({AdminSessionController? sessionController})
      : _sessionController = sessionController ?? AdminSessionController();

  String get _role => _sessionController.getCurrentRole() ?? 'staff';
  String get _backendRole => _sessionController.getCurrentBackendRole() ?? '';

  BackendPermissionMatrix get _matrix => BackendPermissionMatrix(_backendRole);

  bool canOpenRoute(String route) {
    if (_backendRole.isNotEmpty) {
      switch (route) {
        case '/admin/dashboard':
          return _matrix.canViewDashboard();
        case '/admin/owner-dashboard':
          return _backendRole == 'owner';
        case '/admin/reservations':
          return _matrix.canViewReservations();
        case '/admin/housekeeping':
          return _matrix.canManageHousekeeping();
        case '/admin/maintenance':
          return _matrix.canManageMaintenance();
        case '/admin/security':
          return _matrix.canManageSecurity();
        case '/admin/job-notifications':
      case '/admin/notifications':
          return _matrix.canViewDashboard();
        case '/admin/reports':
          return _matrix.canViewRevenue();
        case '/admin/staff':
          return _matrix.canManageStaff();
        case '/admin/settings':
          return _matrix.canViewDashboard();
        default:
          return false;
      }
    }

    switch (route) {
      case '/admin/dashboard':
        return RolePermissions.canViewDashboard(_role);
      case '/admin/owner-dashboard':
        return _role == 'owner';
      case '/admin/reservations':
        return RolePermissions.canViewReservations(_role);
      case '/admin/housekeeping':
        return RolePermissions.canManageHousekeeping(_role);
      case '/admin/maintenance':
        return RolePermissions.canManageMaintenance(_role);
      case '/admin/security':
        return RolePermissions.canManageSecurity(_role);
      case '/admin/job-notifications':
      case '/admin/notifications':
        return RolePermissions.canViewDashboard(_role);
      case '/admin/reports':
        return RolePermissions.canViewRevenue(_role);
      case '/admin/staff':
        return RolePermissions.canManageStaff(_role);
      case '/admin/settings':
        return RolePermissions.canViewDashboard(_role);
      default:
        return false;
    }
  }
}
