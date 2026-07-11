import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../auth/controllers/admin_auth_controller.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../dashboard/controllers/admin_dashboard_controller.dart';
import '../../../dashboard/presentation/widgets/admin_bottom_nav.dart';
import '../../../../data/models/owner_dashboard_model.dart';

class OwnerDashboardPage extends StatefulWidget {
  const OwnerDashboardPage({super.key});

  @override
  State<OwnerDashboardPage> createState() => _OwnerDashboardPageState();
}

class _OwnerDashboardPageState extends State<OwnerDashboardPage> {
  final AdminDashboardController _controller = AdminDashboardController();
  final AdminAuthController _authController = AdminAuthController();
  final AdminAccessController _accessController = AdminAccessController();

  String _period = 'monthly';
  bool _loading = true;
  String? _error;
  OwnerDashboardModel? _data;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _controller.loadOwnerDashboard(period: _period);
      if (!mounted) return;
      setState(() => _data = data);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _logout() async {
    await _authController.logout();
    if (!mounted) return;
    context.go('/admin/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('owner_dashboard')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
        actions: [
          IconButton(
            onPressed: _logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      backgroundColor: AppTheme.lightBg,
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/owner-dashboard',
        showStaffTab: _accessController.canManageStaff(),
        showSecurityTab: _accessController.canManageSecurity(),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          context.tr('failed_load_owner_dashboard', params: {'error': '$_error'}),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 12),
                        FilledButton(onPressed: _load, child: Text(context.tr('retry'))),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      Row(
                        children: [
                          Text(context.tr('period'), style: const TextStyle(fontWeight: FontWeight.w600)),
                          const SizedBox(width: 10),
                          DropdownButton<String>(
                            value: _period,
                            items: [
                              DropdownMenuItem(value: 'daily', child: Text(context.tr('daily'))),
                              DropdownMenuItem(value: 'weekly', child: Text(context.tr('weekly'))),
                              DropdownMenuItem(value: 'monthly', child: Text(context.tr('monthly'))),
                            ],
                            onChanged: (v) {
                              if (v == null) return;
                              setState(() => _period = v);
                              _load();
                            },
                          ),
                          const Spacer(),
                          OutlinedButton(
                            onPressed: () => context.go('/admin/reports'),
                            child: Text(context.tr('detailed_reports')),
                          ),
                          const SizedBox(width: 8),
                          OutlinedButton(
                            onPressed: () => context.go('/admin/settings'),
                            child: Text(context.tr('settings')),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      _card(context.tr('date_range'), '${_data?.startDate ?? '-'} -> ${_data?.endDate ?? '-'}'),
                      _card(context.tr('total_units'), '${_data?.totalUnits ?? 0}'),
                      _card(context.tr('occupancy'), '${_data?.occupancyPercent.toStringAsFixed(2) ?? '0'}%'),
                      _card(context.tr('revenue'), _data?.revenueTotal ?? '0'),
                      _card(context.tr('collections'), _data?.collectionsTotal ?? '0'),
                      _card(context.tr('outstanding'), _data?.outstandingTotal ?? '0'),
                      _card(context.tr('net_income'), _data?.netIncomeTotal ?? '0'),
                      _card(context.tr('pending_housekeeping'), '${_data?.pendingHousekeeping ?? 0}'),
                      _card(context.tr('open_maintenance'), '${_data?.openMaintenance ?? 0}'),
                      _card(context.tr('maintenance_cost'), _data?.maintenanceTotalCost ?? '0'),
                    ],
                  ),
                ),
    );
  }

  Widget _card(String title, String value) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w600))),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, color: AppTheme.primaryNavy)),
        ],
      ),
    );
  }
}
