import '../../../data/models/role_permissions.dart';
import 'backend_permission_matrix.dart';
import 'admin_session_controller.dart';

class AdminAccessController {
  final AdminSessionController _sessionController;

  AdminAccessController({AdminSessionController? sessionController})
      : _sessionController = sessionController ?? AdminSessionController();

  String get _role => _sessionController.getCurrentRole() ?? 'staff';
  String get _backendRole => _sessionController.getCurrentBackendRole() ?? '';

  BackendPermissionMatrix get _matrix => BackendPermissionMatrix(_backendRole);

  bool canViewRevenue() =>
      _backendRole.isNotEmpty ? _matrix.canViewRevenue() : RolePermissions.canViewRevenue(_role);
  bool canManageStaff() =>
      _backendRole.isNotEmpty ? _matrix.canManageStaff() : RolePermissions.canManageStaff(_role);
  bool canManageSecurity() => _backendRole.isNotEmpty
      ? _matrix.canManageSecurity()
      : RolePermissions.canManageSecurity(_role);
  bool canManageMaintenance() => _backendRole.isNotEmpty
      ? _matrix.canManageMaintenance()
      : RolePermissions.canManageMaintenance(_role);
  bool canManageHousekeeping() => _backendRole.isNotEmpty
      ? _matrix.canManageHousekeeping()
      : RolePermissions.canManageHousekeeping(_role);
  bool canViewReservations() => _backendRole.isNotEmpty
      ? _matrix.canViewReservations()
      : RolePermissions.canViewReservations(_role);
  bool canViewDashboard() => _backendRole.isNotEmpty
      ? _matrix.canViewDashboard()
      : RolePermissions.canViewDashboard(_role);

  bool canAccessProperty(String propertyId) {
    return _sessionController.canAccessProperty(propertyId);
  }
}
