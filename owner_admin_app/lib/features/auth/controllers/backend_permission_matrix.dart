class BackendPermissionMatrix {
  final String backendRole;

  const BackendPermissionMatrix(this.backendRole);

  bool get isOwnerAdmin => backendRole == 'owner_admin';
  bool get isOwner => backendRole == 'owner';
  bool get isManager => backendRole == 'manager';
  bool get isReception => backendRole == 'reception';
  bool get isHousekeeping => backendRole == 'housekeeping';
  bool get isMaintenance => backendRole == 'maintenance';

  bool canViewRevenue() => isOwnerAdmin || isOwner || isManager;

  bool canManageStaff() => isOwnerAdmin || isManager;

  bool canManageSecurity() => isOwnerAdmin || isManager;

  bool canManageMaintenance() => isOwnerAdmin || isManager || isMaintenance;

  bool canManageHousekeeping() => isOwnerAdmin || isManager || isHousekeeping;

  bool canViewReservations() =>
      isOwnerAdmin || isManager || isReception || isHousekeeping || isMaintenance;

  bool canViewDashboard() =>
      isOwnerAdmin || isOwner || isManager || isReception || isHousekeeping || isMaintenance;
}
