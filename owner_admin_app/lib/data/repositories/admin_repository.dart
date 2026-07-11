import '../datasources/admin_api.dart';
import '../models/admin_user.dart';
import '../models/dashboard_model.dart';
import '../models/operations_models.dart';
import '../models/owner_dashboard_model.dart';
import '../models/report_models.dart';

class AdminRepository {
  final AdminApi api;

  AdminRepository(this.api);

  Future<AdminUser> login({
    required String email,
    required String password,
  }) {
    return api.login(email: email, password: password);
  }

  Future<Map<String, dynamic>> getRecoveryContact({
    required String loginInput,
  }) {
    return api.getRecoveryContact(loginInput: loginInput);
  }

  Future<DashboardModel> getDashboard({
    required String propertyId,
  }) {
    return api.getDashboard(propertyId: propertyId);
  }

  Future<List<ReservationItem>> getReservations({
    required String propertyId,
  }) {
    return api.getReservations(propertyId: propertyId);
  }

  Future<List<HousekeepingTaskItem>> getHousekeepingTasks({
    required String propertyId,
  }) {
    return api.getHousekeepingTasks(propertyId: propertyId);
  }

  Future<List<MaintenanceItem>> getMaintenanceRequests({
    required String propertyId,
  }) {
    return api.getMaintenanceRequests(propertyId: propertyId);
  }

  Future<List<StaffMemberItem>> getStaff({
    required String propertyId,
  }) {
    return api.getStaff(propertyId: propertyId);
  }

  Future<List<SecurityAlertItem>> getSecurityAlerts({
    required String propertyId,
  }) {
    return api.getSecurityAlerts(propertyId: propertyId);
  }

  Future<void> markNotificationRead(int outboxId) {
    return api.markNotificationRead(outboxId);
  }

  Future<NotificationSettingItem?> getNotificationSetting({
    required String propertyId,
  }) {
    return api.getNotificationSetting(propertyId: propertyId);
  }

  Future<NotificationSettingItem> createNotificationSetting({
    required String propertyId,
    required bool enableWhatsApp,
    required String defaultChannel,
    required String notes,
  }) {
    return api.createNotificationSetting(
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
    return api.updateNotificationSetting(
      settingId: settingId,
      enableWhatsApp: enableWhatsApp,
      defaultChannel: defaultChannel,
      notes: notes,
    );
  }

  Future<void> checkInReservation(int bookingId) {
    return api.checkInReservation(bookingId);
  }

  Future<void> checkOutReservation(int bookingId) {
    return api.checkOutReservation(bookingId);
  }

  Future<void> cancelReservation(int bookingId) {
    return api.cancelReservation(bookingId);
  }

  Future<void> updateHousekeepingStatus({
    required int taskId,
    required String status,
  }) {
    return api.updateHousekeepingStatus(taskId: taskId, status: status);
  }

  Future<void> assignHousekeepingTask({
    required int taskId,
    required int staffId,
  }) {
    return api.assignHousekeepingTask(taskId: taskId, staffId: staffId);
  }

  Future<void> updateMaintenanceStatus({
    required int requestId,
    required String status,
  }) {
    return api.updateMaintenanceStatus(requestId: requestId, status: status);
  }

  Future<void> assignMaintenanceRequest({
    required int requestId,
    required int staffId,
  }) {
    return api.assignMaintenanceRequest(requestId: requestId, staffId: staffId);
  }

  Future<OccupancyReportModel> getOccupancyReport({
    required String propertyId,
    required String period,
  }) {
    return api.getOccupancyReport(propertyId: propertyId, period: period);
  }

  Future<RevenueReportModel> getRevenueReport({
    required String propertyId,
    required String period,
  }) {
    return api.getRevenueReport(propertyId: propertyId, period: period);
  }

  Future<AgingReportModel> getAgingReport({
    required String propertyId,
  }) {
    return api.getAgingReport(propertyId: propertyId);
  }

  Future<OwnerDashboardModel> getOwnerDashboard({
    required String period,
  }) {
    return api.getOwnerDashboard(period: period);
  }
}
