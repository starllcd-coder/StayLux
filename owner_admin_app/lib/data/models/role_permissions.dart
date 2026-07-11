class RolePermissions {
  static const String owner = 'owner';
  static const String manager = 'manager';
  static const String staff = 'staff';

  static bool canViewRevenue(String role) {
    return role == owner || role == manager;
  }

  static bool canManageStaff(String role) {
    return role == owner || role == manager;
  }

  static bool canManageSecurity(String role) {
    return role == owner || role == manager;
  }

  static bool canManageMaintenance(String role) {
    return role == owner || role == manager || role == staff;
  }

  static bool canManageHousekeeping(String role) {
    return role == owner || role == manager || role == staff;
  }

  static bool canViewReservations(String role) {
    return role == owner || role == manager || role == staff;
  }

  static bool canViewDashboard(String role) {
    return role == owner || role == manager || role == staff;
  }
}