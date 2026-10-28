import 'dart:convert';

import '../../core/network/api_exception.dart';
import '../models/admin_user.dart';
import '../models/dashboard_model.dart';
import '../models/operations_models.dart';
import '../models/owner_dashboard_model.dart';
import '../models/report_models.dart';
import '../repositories/token_storage.dart';
import 'api_client.dart';

class AdminApi {
  final ApiClient _client;

  AdminApi({ApiClient? client}) : _client = client ?? ApiClient();

  Future<AdminUser> login({
    required String email,
    required String password,
  }) async {
    if (email.trim().isEmpty || password.trim().isEmpty) {
      throw const ApiException('Email and password are required');
    }

    final tokenResponse = await _client.postJson(
      '/api/auth/token/',
      authenticated: false,
      body: {
        'username': email.trim(),
        'password': password.trim(),
      },
    );

    final accessToken = tokenResponse['access'] as String?;
    final refreshToken = tokenResponse['refresh'] as String?;
    if (accessToken == null || accessToken.isEmpty) {
      throw const ApiException('Login failed: access token was not returned');
    }

    // Seed token cache before fetching profile/property endpoints in this same login flow.
    await TokenStorage.saveTokens(
      token: accessToken,
      refreshToken: refreshToken ?? '',
    );

    final payload = _decodeJwtPayload(accessToken);
    final userId = payload['user_id']?.toString();
    final ownerDashboard = await _tryGetOwnerDashboardWithToken(accessToken);
    if (ownerDashboard != null) {
      final ownerPropertyId = ownerDashboard['property_profile']?.toString() ?? '';
      final propertyIds = ownerPropertyId.isEmpty ? <String>[] : <String>[ownerPropertyId];
      return AdminUser(
        id: userId ?? '',
        name: email.trim(),
        email: email,
        role: 'owner',
        backendRole: 'owner',
        propertyIds: propertyIds,
        token: accessToken,
        refreshToken: refreshToken ?? '',
      );
    }

    final staffProfiles = await _client.getList('/api/staff/', bearerToken: accessToken);
    final properties = await _client.getList('/api/properties/', bearerToken: accessToken);

    final currentProfile = staffProfiles.cast<Map<String, dynamic>>().firstWhere(
          (profile) => profile['user']?['id']?.toString() == userId,
          orElse: () => <String, dynamic>{},
        );

    final propertyIds = <String>[];
    if (currentProfile.isNotEmpty && currentProfile['property'] != null) {
      propertyIds.add(currentProfile['property'].toString());
    } else {
      for (final property in properties) {
        if (property is Map<String, dynamic> && property['id'] != null) {
          propertyIds.add(property['id'].toString());
        }
      }
    }

    final userMap = currentProfile['user'] as Map<String, dynamic>?;
    final name = _buildUserName(userMap, fallback: email.trim());
    final role = _mapBackendRoleToAppRole(
      currentProfile['role']?.toString() ?? '',
      hasAnyStaffProfile: currentProfile.isNotEmpty,
    );
    final backendRole = currentProfile['role']?.toString().trim().isNotEmpty == true
        ? currentProfile['role'].toString()
        : 'owner_admin';

    return AdminUser(
      id: userId ?? '',
      name: name,
      email: email,
      role: role,
      backendRole: backendRole,
      propertyIds: propertyIds,
      token: accessToken,
      refreshToken: refreshToken ?? '',
    );
  }

  Future<Map<String, dynamic>> getRecoveryContact({
    required String loginInput,
  }) async {
    if (loginInput.trim().isEmpty) {
      throw const ApiException('Login input is required');
    }
    return _client.postJson(
      '/api/auth/recovery-contact/',
      authenticated: false,
      body: {'login': loginInput.trim()},
    );
  }

  Future<Map<String, dynamic>?> _tryGetOwnerDashboardWithToken(String accessToken) async {
    try {
      final response = await _client.getMap(
        '/api/reports/owner-dashboard/',
        queryParameters: const {'period': 'monthly'},
        bearerToken: accessToken,
      );
      return response;
    } catch (_) {
      return null;
    }
  }

  Future<DashboardModel> getDashboard({
    required String propertyId,
  }) async {
    final dashboard = await _client.getMap(
      '/api/reports/dashboard/',
      queryParameters: {'property_profile': propertyId},
    );

    return DashboardModel(
      occupancy: (dashboard['occupancy']?['occupancy_percent'] as num?)?.round() ?? 0,
      activeGuests: _toInt(dashboard['units']?['occupied']),
      todayCheckIns: 0,
      todayCheckOuts: 0,
      openMaintenance: _toInt(dashboard['maintenance']?['open']) +
          _toInt(dashboard['maintenance']?['in_progress']),
      openHousekeeping: _toInt(dashboard['housekeeping']?['pending']) +
          _toInt(dashboard['housekeeping']?['in_progress']),
      activeAlerts: 0,
      revenueToday: dashboard['billing']?['revenue_total']?.toString() ?? '0',
      recentActivities: [
        ActivityModel(
          title: 'Occupancy',
          subtitle:
              '${(dashboard['occupancy']?['occupancy_percent'] ?? 0).toString()}% in selected period',
        ),
        ActivityModel(
          title: 'Collections',
          subtitle:
              'Collected ${dashboard['billing']?['collections_total'] ?? '0'} for selected period',
        ),
        ActivityModel(
          title: 'Housekeeping',
          subtitle: '${dashboard['housekeeping']?['total_tasks'] ?? 0} tasks',
        ),
        ActivityModel(
          title: 'Maintenance',
          subtitle: '${dashboard['maintenance']?['total_requests'] ?? 0} requests',
        ),
      ],
    );
  }

  Future<List<ReservationItem>> getReservations({
    required String propertyId,
  }) async {
    final data = await _client.getList(
      '/api/bookings/',
      queryParameters: {'property_profile': propertyId},
    );

    return data
        .whereType<Map<String, dynamic>>()
        .map(
          (item) => ReservationItem(
            id: _toInt(item['id']),
            guestLabel: item['guest']?.toString() ?? 'Guest #${item['id'] ?? ''}',
            unitLabel: item['unit']?.toString() ?? '-',
            status: item['status']?.toString() ?? 'unknown',
            stayLabel:
                '${item['start_date']?.toString() ?? '-'} to ${item['end_date']?.toString() ?? '-'}',
            startDate: item['start_date']?.toString() ?? '',
            endDate: item['end_date']?.toString() ?? '',
            bookingType: item['booking_type']?.toString() ?? '',
            createdAt: item['created_at']?.toString() ?? '',
            updatedAt: item['updated_at']?.toString() ?? '',
          ),
        )
        .toList();
  }

  Future<List<HousekeepingTaskItem>> getHousekeepingTasks({
    required String propertyId,
  }) async {
    final data = await _client.getList(
      '/api/housekeeping/',
      queryParameters: {'property_profile': propertyId},
    );

    return data
        .whereType<Map<String, dynamic>>()
        .map(
          (item) => HousekeepingTaskItem(
            id: _toInt(item['id']),
            title: item['title']?.toString() ?? 'Housekeeping task',
            unitLabel: item['unit']?.toString() ?? '-',
            status: item['status']?.toString() ?? 'pending',
            priority: item['priority']?.toString() ?? 'normal',
            assignedTo: item['assigned_to']?.toString() ?? 'Unassigned',
            assignedToId: _toNullableInt(item['assigned_to']),
            createdAt: item['created_at']?.toString() ?? '',
            updatedAt: item['updated_at']?.toString() ?? '',
            completedAt: item['completed_at']?.toString() ?? '',
          ),
        )
        .toList();
  }

  Future<List<MaintenanceItem>> getMaintenanceRequests({
    required String propertyId,
  }) async {
    final data = await _client.getList(
      '/api/maintenance/',
      queryParameters: {'property_profile': propertyId},
    );

    return data
        .whereType<Map<String, dynamic>>()
        .map(
          (item) => MaintenanceItem(
            id: _toInt(item['id']),
            title: item['title']?.toString() ?? 'Maintenance request',
            unitLabel: item['unit']?.toString() ?? '-',
            status: item['status']?.toString() ?? 'open',
            priority: item['priority']?.toString() ?? 'normal',
            assignedTo: item['assigned_to']?.toString() ?? 'Unassigned',
            assignedToId: _toNullableInt(item['assigned_to']),
            createdAt: item['created_at']?.toString() ?? '',
            updatedAt: item['updated_at']?.toString() ?? '',
            resolvedAt: item['resolved_at']?.toString() ?? '',
          ),
        )
        .toList();
  }

  Future<List<StaffMemberItem>> getStaff({
    required String propertyId,
  }) async {
    final data = await _client.getList(
      '/api/staff/',
      queryParameters: {'property': propertyId},
    );

    return data.whereType<Map<String, dynamic>>().map((item) {
      final user = item['user'] as Map<String, dynamic>?;
      return StaffMemberItem(
        id: _toInt(item['id']),
        name: _buildUserName(user, fallback: 'Staff #${item['id']}'),
        role: item['role']?.toString() ?? 'staff',
        isActive: item['is_active'] == true,
      );
    }).toList();
  }

  Future<List<SecurityAlertItem>> getSecurityAlerts({
    required String propertyId,
  }) async {
    final data = await _client.getList(
      '/api/outbox/',
      queryParameters: {'property_profile': propertyId},
    );

    return data.whereType<Map<String, dynamic>>().map((item) {
      final eventKey = item['event_key']?.toString();
      return SecurityAlertItem(
        id: _toInt(item['id']),
        title: (eventKey == null || eventKey.trim().isEmpty) ? 'Security event' : eventKey,
        channel: item['channel']?.toString() ?? '-',
        status: item['status']?.toString() ?? 'pending',
        createdAt: item['created_at']?.toString() ?? '',
        isRead: item['is_read'] == true,
        content: item['content']?.toString() ?? '',
        error: item['error']?.toString() ?? '',
      );
    }).toList();
  }

  Future<void> markNotificationRead(int outboxId) async {
    await _client.patchJson(
      '/api/outbox/$outboxId/',
      body: {'is_read': true},
    );
  }

  Future<NotificationSettingItem?> getNotificationSetting({
    required String propertyId,
  }) async {
    final data = await _client.getList(
      '/api/notification-settings/',
      queryParameters: {'property_profile': propertyId},
    );
    if (data.isEmpty) return null;
    final item = data.first;
    if (item is! Map<String, dynamic>) return null;
    return NotificationSettingItem(
      id: _toInt(item['id']),
      propertyProfile: item['property_profile']?.toString() ?? propertyId,
      enableWhatsApp: item['enable_whatsapp'] == true,
      defaultChannel: item['default_channel']?.toString() ?? 'whatsapp',
      notes: item['notes']?.toString() ?? '',
    );
  }

  Future<NotificationSettingItem> createNotificationSetting({
    required String propertyId,
    required bool enableWhatsApp,
    required String defaultChannel,
    required String notes,
  }) async {
    final created = await _client.postJson(
      '/api/notification-settings/',
      body: {
        'property_profile': int.tryParse(propertyId) ?? propertyId,
        'enable_whatsapp': enableWhatsApp,
        'default_channel': defaultChannel,
        'notes': notes,
      },
    );

    return NotificationSettingItem(
      id: _toInt(created['id']),
      propertyProfile: created['property_profile']?.toString() ?? propertyId,
      enableWhatsApp: created['enable_whatsapp'] == true,
      defaultChannel: created['default_channel']?.toString() ?? defaultChannel,
      notes: created['notes']?.toString() ?? notes,
    );
  }

  Future<NotificationSettingItem> updateNotificationSetting({
    required int settingId,
    required bool enableWhatsApp,
    required String defaultChannel,
    required String notes,
  }) async {
    final updated = await _client.patchJson(
      '/api/notification-settings/$settingId/',
      body: {
        'enable_whatsapp': enableWhatsApp,
        'default_channel': defaultChannel,
        'notes': notes,
      },
    );

    return NotificationSettingItem(
      id: _toInt(updated['id']),
      propertyProfile: updated['property_profile']?.toString() ?? '',
      enableWhatsApp: updated['enable_whatsapp'] == true,
      defaultChannel: updated['default_channel']?.toString() ?? defaultChannel,
      notes: updated['notes']?.toString() ?? notes,
    );
  }

  Future<void> checkInReservation(int bookingId) async {
    await _client.postJson('/api/bookings/$bookingId/check_in/', body: const {});
  }

  Future<void> checkOutReservation(int bookingId) async {
    await _client.postJson('/api/bookings/$bookingId/check_out/', body: const {});
  }

  Future<void> cancelReservation(int bookingId) async {
    await _client.postJson('/api/bookings/$bookingId/cancel/', body: const {});
  }

  Future<void> updateHousekeepingStatus({
    required int taskId,
    required String status,
  }) async {
    await _client.patchJson(
      '/api/housekeeping/$taskId/',
      body: {'status': status},
    );
  }

  Future<void> assignHousekeepingTask({
    required int taskId,
    required int staffId,
  }) async {
    await _client.postJson(
      '/api/housekeeping/$taskId/assign/',
      body: {'assigned_to': staffId},
    );
  }

  Future<void> updateMaintenanceStatus({
    required int requestId,
    required String status,
  }) async {
    await _client.patchJson(
      '/api/maintenance/$requestId/',
      body: {'status': status},
    );
  }

  Future<void> assignMaintenanceRequest({
    required int requestId,
    required int staffId,
  }) async {
    await _client.postJson(
      '/api/maintenance/$requestId/assign/',
      body: {'assigned_to': staffId},
    );
  }

  Future<OccupancyReportModel> getOccupancyReport({
    required String propertyId,
    required String period,
  }) async {
    final data = await _client.getMap(
      '/api/reports/occupancy/',
      queryParameters: {
        'property_profile': propertyId,
        'period': period,
      },
    );

    return OccupancyReportModel(
      totalUnits: _toInt(data['total_units']),
      totalUnitNights: _toInt(data['total_unit_nights']),
      bookedNights: _toInt(data['booked_nights']),
      occupancyPercent: _toDouble(data['occupancy_percent']),
      activeBookingsCount: _toInt(data['active_bookings_count']),
    );
  }

  Future<RevenueReportModel> getRevenueReport({
    required String propertyId,
    required String period,
  }) async {
    final data = await _client.getMap(
      '/api/reports/revenue/',
      queryParameters: {
        'property_profile': propertyId,
        'period': period,
      },
    );

    final invoices = data['invoices'] as Map<String, dynamic>? ?? const {};
    final payments = data['payments'] as Map<String, dynamic>? ?? const {};
    return RevenueReportModel(
      revenueTotal: invoices['revenue_total']?.toString() ?? '0',
      taxTotal: invoices['tax_total']?.toString() ?? '0',
      outstandingTotal: invoices['outstanding_total']?.toString() ?? '0',
      collectionsTotal: payments['collections_total']?.toString() ?? '0',
    );
  }

  Future<AgingReportModel> getAgingReport({
    required String propertyId,
  }) async {
    final data = await _client.getMap(
      '/api/reports/aging/',
      queryParameters: {'property_profile': propertyId},
    );

    final rawBuckets = data['buckets'] as List<dynamic>? ?? const [];
    final buckets = rawBuckets.whereType<Map<String, dynamic>>().map((b) {
      return AgingBucketModel(
        label: b['label']?.toString() ?? '-',
        count: _toInt(b['count']),
        amount: b['amount']?.toString() ?? '0',
      );
    }).toList();

    return AgingReportModel(
      totalOutstanding: data['total_outstanding']?.toString() ?? '0',
      buckets: buckets,
    );
  }

  Future<OwnerDashboardModel> getOwnerDashboard({
    required String period,
  }) async {
    final data = await _client.getMap(
      '/api/reports/owner-dashboard/',
      queryParameters: {'period': period},
    );

    return OwnerDashboardModel(
      propertyProfile: data['property_profile']?.toString() ?? '',
      period: data['period']?.toString() ?? period,
      startDate: data['range']?['start_date']?.toString() ?? '',
      endDate: data['range']?['end_date']?.toString() ?? '',
      totalUnits: _toInt(data['units']?['total_units']),
      occupancyPercent: _toDouble(data['occupancy']?['occupancy_percent']),
      revenueTotal: data['billing']?['revenue_total']?.toString() ?? '0',
      collectionsTotal: data['billing']?['collections_total']?.toString() ?? '0',
      outstandingTotal: data['billing']?['outstanding_total']?.toString() ?? '0',
      netIncomeTotal: data['billing']?['net_income_total']?.toString() ?? '0',
      pendingHousekeeping: _toInt(data['housekeeping']?['pending']),
      openMaintenance: _toInt(data['maintenance']?['open']),
      maintenanceTotalCost: data['maintenance']?['total_cost']?.toString() ?? '0',
    );
  }

  Map<String, dynamic> _decodeJwtPayload(String token) {
    final parts = token.split('.');
    if (parts.length < 2) return const {};

    try {
      final normalized = base64Url.normalize(parts[1]);
      final payload = utf8.decode(base64Url.decode(normalized));
      final decoded = jsonDecode(payload);
      if (decoded is Map<String, dynamic>) return decoded;
    } catch (_) {
      return const {};
    }
    return const {};
  }

  String _mapBackendRoleToAppRole(String backendRole, {required bool hasAnyStaffProfile}) {
    switch (backendRole) {
      case 'owner_admin':
        return 'owner';
      case 'manager':
        return 'manager';
      case 'accounts':
        return 'accounts';
      case 'reception':
      case 'housekeeping':
      case 'maintenance':
        return 'staff';
      default:
        return hasAnyStaffProfile ? 'staff' : 'owner';
    }
  }

  String _buildUserName(Map<String, dynamic>? user, {required String fallback}) {
    if (user == null) return fallback;
    final first = (user['first_name'] ?? '').toString().trim();
    final last = (user['last_name'] ?? '').toString().trim();
    final fullName = '$first $last'.trim();
    if (fullName.isNotEmpty) return fullName;
    final username = (user['username'] ?? '').toString().trim();
    if (username.isNotEmpty) return username;
    return fallback;
  }

  int _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  double _toDouble(dynamic value) {
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0;
    return 0;
  }

  int? _toNullableInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }
}
