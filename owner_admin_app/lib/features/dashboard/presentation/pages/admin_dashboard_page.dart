import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/admin_property.dart';
import '../../../../data/models/dashboard_model.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../auth/controllers/admin_auth_controller.dart';
import '../../../auth/controllers/admin_session_controller.dart';
import '../../controllers/admin_dashboard_controller.dart';
import '../../controllers/selected_property_controller.dart';
import '../widgets/admin_bottom_nav.dart';
import '../widgets/dashboard_widgets.dart';

class AdminDashboardPage extends StatefulWidget {
  const AdminDashboardPage({super.key});

  @override
  State<AdminDashboardPage> createState() => _AdminDashboardPageState();
}

class _AdminDashboardPageState extends State<AdminDashboardPage> {
  final AdminDashboardController _controller = AdminDashboardController();
  final AdminAuthController _authController = AdminAuthController();
  final AdminSessionController _sessionController = AdminSessionController();
  final AdminAccessController _accessController = AdminAccessController();

  late Future<DashboardModel> _dashboardFuture;

  List<AdminProperty> get _availableProperties {
    final ids = _sessionController.getPropertyIds();
    return ids
        .map((id) => AdminProperty(id: id, name: 'Property $id', city: ''))
        .toList();
  }

  @override
  void initState() {
    super.initState();
    SelectedPropertyController.ensureDefault(
      _sessionController.getPropertyIds(),
    );
    _dashboardFuture = _loadDashboardForSelectedProperty();
  }

  Future<DashboardModel> _loadDashboardForSelectedProperty() {
    final selectedPropertyId = SelectedPropertyController.selectedPropertyId;
    if (selectedPropertyId == null || selectedPropertyId.isEmpty) {
      throw Exception('No property assigned to this user');
    }
    return _controller.loadDashboard(propertyId: selectedPropertyId);
  }

  IconData _iconForTitle(String title) {
    switch (title) {
      case 'Reservations':
        return Icons.book_online_outlined;
      case 'Housekeeping':
        return Icons.cleaning_services_outlined;
      case 'Maintenance':
        return Icons.build_outlined;
      case 'Security':
        return Icons.shield_outlined;
      case 'Notifications':
        return Icons.notifications_active_outlined;
      case 'Reports':
        return Icons.bar_chart_outlined;
      case 'Settings':
        return Icons.settings_outlined;
      case 'Staff':
        return Icons.people_outline;
      default:
        return Icons.dashboard_outlined;
    }
  }

  String _localizedActionTitle(BuildContext context, String title) {
    switch (title) {
      case 'Reservations':
        return context.tr('bookings');
      case 'Housekeeping':
        return context.tr('housekeeping');
      case 'Maintenance':
        return context.tr('maintenance');
      case 'Security':
        return context.tr('security');
      case 'Notifications':
        return context.tr('notifications');
      case 'Reports':
        return context.tr('reports');
      case 'Settings':
        return context.tr('settings');
      case 'Staff':
        return context.tr('staff');
      default:
        return title;
    }
  }

  String _localizedActivityTitle(BuildContext context, String title) {
    switch (title) {
      case 'Occupancy':
        return context.tr('occupancy');
      case 'Collections':
        return context.tr('collections');
      case 'Housekeeping':
        return context.tr('housekeeping');
      case 'Maintenance':
        return context.tr('maintenance');
      default:
        return title;
    }
  }

  String _localizedActivitySubtitle(BuildContext context, ActivityModel item) {
    if (item.title == 'Occupancy') {
      final match = RegExp(r'([0-9]+(?:\.[0-9]+)?)%').firstMatch(item.subtitle);
      final value = match?.group(1) ?? '0';
      return context.tr('activity_occupancy_subtitle', params: {'value': value});
    }
    if (item.title == 'Collections') {
      final match = RegExp(r'Collected\s+([0-9]+(?:\.[0-9]+)?)').firstMatch(item.subtitle);
      final value = match?.group(1) ?? '0';
      return context.tr('activity_collections_subtitle', params: {'value': value});
    }
    if (item.title == 'Housekeeping') {
      final match = RegExp(r'([0-9]+)').firstMatch(item.subtitle);
      final value = match?.group(1) ?? '0';
      return context.tr('activity_tasks_subtitle', params: {'value': value});
    }
    if (item.title == 'Maintenance') {
      final match = RegExp(r'([0-9]+)').firstMatch(item.subtitle);
      final value = match?.group(1) ?? '0';
      return context.tr('activity_requests_subtitle', params: {'value': value});
    }
    return item.subtitle;
  }

  Future<void> _logout() async {
    await _authController.logout();
    SelectedPropertyController.clear();
    if (!mounted) return;
    context.go('/admin/login');
  }

  @override
  Widget build(BuildContext context) {
    final userName = _sessionController.getCurrentUserName() ?? 'Admin';
    final role = _sessionController.getCurrentRole() ?? 'staff';
    final selectedPropertyId = SelectedPropertyController.selectedPropertyId;
    final actions = AdminDashboardController.visibleQuickActions(
      canViewReservations: _accessController.canViewReservations(),
      canManageHousekeeping: _accessController.canManageHousekeeping(),
      canManageMaintenance: _accessController.canManageMaintenance(),
      canManageSecurity: _accessController.canManageSecurity(),
      canViewRevenue: _accessController.canViewRevenue(),
      canManageStaff: _accessController.canManageStaff(),
    );

    return Scaffold(
      backgroundColor: AppTheme.lightBg,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        surfaceTintColor: Colors.white,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('staylux_admin'),
              style: TextStyle(
                color: AppTheme.primaryNavy,
                fontWeight: FontWeight.w700,
              ),
            ),
            Text(
              '$userName - ${role.toUpperCase()}',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _logout,
            icon: const Icon(Icons.logout, color: AppTheme.primaryNavy),
          ),
        ],
      ),
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/dashboard',
        showStaffTab: _accessController.canManageStaff(),
        showSecurityTab: _accessController.canManageSecurity(),
      ),
      body: FutureBuilder<DashboardModel>(
        future: _dashboardFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      context.tr(
                        'failed_load_dashboard',
                        params: {'error': '${snapshot.error}'},
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: () {
                        setState(() {
                          _dashboardFuture =
                              _loadDashboardForSelectedProperty();
                        });
                      },
                      child: Text(context.tr('retry')),
                    ),
                  ],
                ),
              ),
            );
          }

          final dashboard = snapshot.data!;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    gradient: const LinearGradient(
                      colors: [AppTheme.primaryNavy, Color(0xFF13385D)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.tr('property_operations_monitor'),
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 26,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        context.tr('track_operations_line'),
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 14,
                          height: 1.5,
                        ),
                      ),
                      const SizedBox(height: 18),
                      DropdownButtonFormField<String>(
                        initialValue: selectedPropertyId,
                        dropdownColor: AppTheme.primaryNavy,
                        decoration: InputDecoration(
                          filled: true,
                          fillColor: Colors.white.withValues(alpha: 0.08),
                          hintText: context.tr('select_property'),
                          hintStyle: const TextStyle(color: Colors.white70),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(14),
                            borderSide: BorderSide.none,
                          ),
                        ),
                        style: const TextStyle(color: Colors.white),
                        items: _availableProperties.map((property) {
                          return DropdownMenuItem<String>(
                            value: property.id,
                            child: Text(property.name),
                          );
                        }).toList(),
                        onChanged: (value) {
                          if (value == null) return;
                          setState(() {
                            SelectedPropertyController.setSelectedProperty(
                              value,
                            );
                            _dashboardFuture =
                                _loadDashboardForSelectedProperty();
                          });
                        },
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                DashboardSectionTitle(
                  title: context.tr('overview'),
                  subtitle: context.tr('overview_subtitle'),
                ),
                const SizedBox(height: 14),
                GridView.count(
                  crossAxisCount: MediaQuery.of(context).size.width > 900
                      ? 4
                      : 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.08,
                  children: [
                    DashboardStatCard(
                      title: context.tr('occupancy'),
                      value: '${dashboard.occupancy}%',
                      icon: Icons.apartment_outlined,
                      subtitle: context.tr('current_occupied_rooms'),
                    ),
                    DashboardStatCard(
                      title: context.tr('active_guests'),
                      value: '${dashboard.activeGuests}',
                      icon: Icons.badge_outlined,
                      subtitle: context.tr('guests_checked_in'),
                    ),
                    DashboardStatCard(
                      title: context.tr('open_housekeeping'),
                      value: '${dashboard.openHousekeeping}',
                      icon: Icons.cleaning_services_outlined,
                      subtitle: context.tr('pending_cleaning_tasks'),
                    ),
                    if (_accessController.canViewRevenue())
                      DashboardStatCard(
                        title: context.tr('revenue'),
                        value: dashboard.revenueToday,
                        icon: Icons.payments_outlined,
                        subtitle: context.tr('revenue_selected_period'),
                      ),
                  ],
                ),
                const SizedBox(height: 24),
                DashboardSectionTitle(
                  title: context.tr('quick_access'),
                  subtitle: context.tr('quick_access_subtitle'),
                ),
                const SizedBox(height: 14),
                Column(
                  children: actions.map((action) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: DashboardActionCard(
                        title: _localizedActionTitle(context, action['title']!),
                        icon: _iconForTitle(action['title']!),
                        onTap: () => context.go(action['route']!),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 24),
                DashboardSectionTitle(
                  title: context.tr('today_snapshot'),
                  subtitle: context.tr('today_snapshot_subtitle'),
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: _MiniInfoCard(
                        title: context.tr('check_ins'),
                        value: '${dashboard.todayCheckIns}',
                        color: Colors.green,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _MiniInfoCard(
                        title: context.tr('check_outs'),
                        value: '${dashboard.todayCheckOuts}',
                        color: Colors.orange,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _MiniInfoCard(
                        title: context.tr('alerts'),
                        value: '${dashboard.activeAlerts}',
                        color: Colors.red,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                DashboardSectionTitle(
                  title: context.tr('recent_activity'),
                  subtitle: context.tr('recent_activity_subtitle'),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(22),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.05),
                        blurRadius: 14,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: Column(
                    children: dashboard.recentActivities.map((item) {
                      return ActivityTile(
                        title: _localizedActivityTitle(context, item.title),
                        subtitle: _localizedActivitySubtitle(context, item),
                      );
                    }).toList(),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _MiniInfoCard extends StatelessWidget {
  final String title;
  final String value;
  final Color color;

  const _MiniInfoCard({
    required this.title,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: color.withValues(alpha: 0.12),
            child: Icon(Icons.circle, size: 14, color: color),
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: AppTheme.primaryNavy,
            ),
          ),
          const SizedBox(height: 4),
          Text(title),
        ],
      ),
    );
  }
}
