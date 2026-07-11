import '../../../data/datasources/admin_api.dart';
import '../../../data/models/dashboard_model.dart';
import '../../../data/models/operations_models.dart';
import '../../../data/models/owner_dashboard_model.dart';
import '../../../data/models/report_models.dart';
import '../../../data/repositories/admin_repository.dart';

class AdminDashboardController {
  final AdminRepository _repository = AdminRepository(AdminApi());

  Future<DashboardModel> loadDashboard({
    required String propertyId,
  }) async {
    return _repository.getDashboard(propertyId: propertyId);
  }

  Future<List<ReservationItem>> loadReservations({
    required String propertyId,
  }) {
    return _repository.getReservations(propertyId: propertyId);
  }

  Future<List<HousekeepingTaskItem>> loadHousekeeping({
    required String propertyId,
  }) {
    return _repository.getHousekeepingTasks(propertyId: propertyId);
  }

  Future<List<MaintenanceItem>> loadMaintenance({
    required String propertyId,
  }) {
    return _repository.getMaintenanceRequests(propertyId: propertyId);
  }

  Future<List<StaffMemberItem>> loadStaff({
    required String propertyId,
  }) {
    return _repository.getStaff(propertyId: propertyId);
  }

  Future<List<SecurityAlertItem>> loadSecurityAlerts({
    required String propertyId,
  }) {
    return _repository.getSecurityAlerts(propertyId: propertyId);
  }

  Future<void> markNotificationRead(int outboxId) {
    return _repository.markNotificationRead(outboxId);
  }

  Future<NotificationSettingItem?> loadNotificationSetting({
    required String propertyId,
  }) {
    return _repository.getNotificationSetting(propertyId: propertyId);
  }

  Future<NotificationSettingItem> createNotificationSetting({
    required String propertyId,
    required bool enableWhatsApp,
    required String defaultChannel,
    required String notes,
  }) {
    return _repository.createNotificationSetting(
      propertyId: propertyId,
      enableWhatsApp: enableWhatsApp,
      defaultChannel: defaultChannel,
      notes: notes,
    );
  }

  Future<NotificationSettingItem> updateNotificationSetting({
    required int settingId,
    required bool enableWhatsApp,
    required String defaultChannel,
    required String notes,
  }) {
    return _repository.updateNotificationSetting(
      settingId: settingId,
      enableWhatsApp: enableWhatsApp,
      defaultChannel: defaultChannel,
      notes: notes,
    );
  }

  Future<void> checkInReservation(int bookingId) {
    return _repository.checkInReservation(bookingId);
  }

  Future<void> checkOutReservation(int bookingId) {
    return _repository.checkOutReservation(bookingId);
  }

  Future<void> cancelReservation(int bookingId) {
    return _repository.cancelReservation(bookingId);
  }

  Future<void> updateHousekeepingStatus({
    required int taskId,
    required String status,
  }) {
    return _repository.updateHousekeepingStatus(taskId: taskId, status: status);
  }

  Future<void> assignHousekeepingTask({
    required int taskId,
    required int staffId,
  }) {
    return _repository.assignHousekeepingTask(taskId: taskId, staffId: staffId);
  }

  Future<void> updateMaintenanceStatus({
    required int requestId,
    required String status,
  }) {
    return _repository.updateMaintenanceStatus(requestId: requestId, status: status);
  }

  Future<void> assignMaintenanceRequest({
    required int requestId,
    required int staffId,
  }) {
    return _repository.assignMaintenanceRequest(requestId: requestId, staffId: staffId);
  }

  Future<OccupancyReportModel> loadOccupancyReport({
    required String propertyId,
    required String period,
  }) {
    return _repository.getOccupancyReport(propertyId: propertyId, period: period);
  }

  Future<RevenueReportModel> loadRevenueReport({
    required String propertyId,
    required String period,
  }) {
    return _repository.getRevenueReport(propertyId: propertyId, period: period);
  }

  Future<AgingReportModel> loadAgingReport({
    required String propertyId,
  }) {
    return _repository.getAgingReport(propertyId: propertyId);
  }

  Future<OwnerDashboardModel> loadOwnerDashboard({
    required String period,
  }) {
    return _repository.getOwnerDashboard(period: period);
  }

  static const List<Map<String, String>> quickActions = [
    {'title': 'Reservations', 'route': '/admin/reservations'},
    {'title': 'Housekeeping', 'route': '/admin/housekeeping'},
    {'title': 'Maintenance', 'route': '/admin/maintenance'},
    {'title': 'Security', 'route': '/admin/security'},
    {'title': 'Notifications', 'route': '/admin/notifications'},
    {'title': 'Reports', 'route': '/admin/reports'},
    {'title': 'Settings', 'route': '/admin/settings'},
    {'title': 'Staff', 'route': '/admin/staff'},
  ];

  static List<Map<String, String>> visibleQuickActions({
    required bool canViewReservations,
    required bool canManageHousekeeping,
    required bool canManageMaintenance,
    required bool canManageSecurity,
    required bool canViewRevenue,
    required bool canManageStaff,
  }) {
    return quickActions.where((action) {
      final title = action['title']!;
      if (title == 'Reservations') return canViewReservations;
      if (title == 'Housekeeping') return canManageHousekeeping;
      if (title == 'Maintenance') return canManageMaintenance;
      if (title == 'Security') return canManageSecurity;
      if (title == 'Reports') return canViewRevenue;
      if (title == 'Staff') return canManageStaff;
      return true;
    }).toList();
  }
}
