import 'package:flutter/material.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/services/telemetry_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/owner_dashboard_model.dart';
import '../../../../data/models/report_models.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../auth/controllers/admin_session_controller.dart';
import '../../../dashboard/controllers/admin_dashboard_controller.dart';
import '../../../dashboard/controllers/selected_property_controller.dart';
import '../../../dashboard/presentation/widgets/admin_bottom_nav.dart';

class ReportsPage extends StatefulWidget {
  final AdminAccessController? accessController;
  final AdminSessionController? sessionController;
  final AdminDashboardController? dashboardController;

  const ReportsPage({
    super.key,
    this.accessController,
    this.sessionController,
    this.dashboardController,
  });

  @override
  State<ReportsPage> createState() => _ReportsPageState();
}

class _ReportsPageState extends State<ReportsPage> {
  late final AdminAccessController _access;
  late final AdminSessionController _sessionController;
  late final AdminDashboardController _controller;

  bool _isLoading = true;
  String? _error;
  String _period = 'monthly';

  OccupancyReportModel? _occupancy;
  RevenueReportModel? _revenue;
  AgingReportModel? _aging;
  OwnerDashboardModel? _ownerDashboard;

  final Map<String, double> _occupancyByPeriod = {};
  final Map<String, String> _revenueByPeriod = {};

  String _periodLabel(String value) {
    if (value == 'daily') return context.tr('daily');
    if (value == 'weekly') return context.tr('weekly');
    if (value == 'monthly') return context.tr('monthly');
    return value;
  }

  @override
  void initState() {
    super.initState();
    _access = widget.accessController ?? AdminAccessController();
    _sessionController = widget.sessionController ?? AdminSessionController();
    _controller = widget.dashboardController ?? AdminDashboardController();
    TelemetryService.instance.trackScreen('reports');
    SelectedPropertyController.ensureDefault(_sessionController.getPropertyIds());
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final backendRole = _sessionController.getCurrentBackendRole() ?? '';
      final isOwner = backendRole == 'owner';

      if (isOwner) {
        final ownerData = await _controller.loadOwnerDashboard(period: _period);
        if (!mounted) return;
        setState(() {
          _ownerDashboard = ownerData;
          _occupancy = null;
          _revenue = null;
          _aging = null;
          _occupancyByPeriod
            ..clear()
            ..addAll({
              'daily': ownerData.occupancyPercent,
              'weekly': ownerData.occupancyPercent,
              'monthly': ownerData.occupancyPercent,
            });
          _revenueByPeriod
            ..clear()
            ..addAll({
              'daily': ownerData.revenueTotal,
              'weekly': ownerData.revenueTotal,
              'monthly': ownerData.revenueTotal,
            });
        });
        return;
      }

      final propertyId = SelectedPropertyController.selectedPropertyId;
      if (propertyId == null || propertyId.isEmpty) {
        throw Exception('No property selected');
      }

      final results = await Future.wait([
        _controller.loadOccupancyReport(propertyId: propertyId, period: _period),
        _controller.loadRevenueReport(propertyId: propertyId, period: _period),
        _controller.loadAgingReport(propertyId: propertyId),
        _controller.loadOccupancyReport(propertyId: propertyId, period: 'daily'),
        _controller.loadOccupancyReport(propertyId: propertyId, period: 'weekly'),
        _controller.loadOccupancyReport(propertyId: propertyId, period: 'monthly'),
        _controller.loadRevenueReport(propertyId: propertyId, period: 'daily'),
        _controller.loadRevenueReport(propertyId: propertyId, period: 'weekly'),
        _controller.loadRevenueReport(propertyId: propertyId, period: 'monthly'),
      ]);

      if (!mounted) return;
      final occDaily = results[3] as OccupancyReportModel;
      final occWeekly = results[4] as OccupancyReportModel;
      final occMonthly = results[5] as OccupancyReportModel;
      final revDaily = results[6] as RevenueReportModel;
      final revWeekly = results[7] as RevenueReportModel;
      final revMonthly = results[8] as RevenueReportModel;

      setState(() {
        _occupancy = results[0] as OccupancyReportModel;
        _revenue = results[1] as RevenueReportModel;
        _aging = results[2] as AgingReportModel;
        _ownerDashboard = null;
        _occupancyByPeriod
          ..clear()
          ..addAll({
            'daily': occDaily.occupancyPercent,
            'weekly': occWeekly.occupancyPercent,
            'monthly': occMonthly.occupancyPercent,
          });
        _revenueByPeriod
          ..clear()
          ..addAll({
            'daily': revDaily.revenueTotal,
            'weekly': revWeekly.revenueTotal,
            'monthly': revMonthly.revenueTotal,
          });
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('reports')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      backgroundColor: AppTheme.lightBg,
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/reports',
        showStaffTab: _access.canManageStaff(),
        showSecurityTab: _access.canManageSecurity(),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          context.tr('failed_load_reports', params: {'error': '$_error'}),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 10),
                        FilledButton(onPressed: _load, child: Text(context.tr('retry'))),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final wide = constraints.maxWidth >= 960;
                      final cards = _buildCards();

                      return ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          Row(
                            children: [
                              Text(context.tr('period'), style: const TextStyle(fontWeight: FontWeight.w600)),
                              const SizedBox(width: 12),
                              DropdownButton<String>(
                                value: _period,
                                items: [
                                  DropdownMenuItem(value: 'daily', child: Text(context.tr('daily'))),
                                  DropdownMenuItem(value: 'weekly', child: Text(context.tr('weekly'))),
                                  DropdownMenuItem(value: 'monthly', child: Text(context.tr('monthly'))),
                                ],
                                onChanged: (value) {
                                  if (value == null) return;
                                  setState(() => _period = value);
                                  _load();
                                },
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          if (!wide)
                            ...cards.map(
                              (c) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: c,
                              ),
                            ),
                          if (wide)
                            Wrap(
                              spacing: 12,
                              runSpacing: 12,
                              children: cards
                                  .map((c) => SizedBox(width: (constraints.maxWidth - 44) / 2, child: c))
                                  .toList(),
                            ),
                        ],
                      );
                    },
                  ),
                ),
    );
  }

  List<Widget> _buildCards() {
    final cards = <Widget>[
      _ReportCard(
        title: context.tr('trends'),
        rows: [
          _row(context.tr('daily_occupancy'), '${_occupancyByPeriod['daily']?.toStringAsFixed(2) ?? '0'}%'),
          _meter(value: ((_occupancyByPeriod['daily'] ?? 0) / 100).clamp(0, 1), color: Colors.blue),
          const SizedBox(height: 8),
          _row(context.tr('weekly_occupancy'), '${_occupancyByPeriod['weekly']?.toStringAsFixed(2) ?? '0'}%'),
          _meter(value: ((_occupancyByPeriod['weekly'] ?? 0) / 100).clamp(0, 1), color: Colors.indigo),
          const SizedBox(height: 8),
          _row(context.tr('monthly_occupancy'), '${_occupancyByPeriod['monthly']?.toStringAsFixed(2) ?? '0'}%'),
          _meter(value: ((_occupancyByPeriod['monthly'] ?? 0) / 100).clamp(0, 1), color: Colors.deepPurple),
          const SizedBox(height: 8),
          _row(context.tr('daily_revenue'), _revenueByPeriod['daily'] ?? '0'),
          _row(context.tr('weekly_revenue'), _revenueByPeriod['weekly'] ?? '0'),
          _row(context.tr('monthly_revenue'), _revenueByPeriod['monthly'] ?? '0'),
        ],
      ),
    ];

    if (_ownerDashboard != null) {
      cards.add(
        _ReportCard(
          title: context.tr('owner_summary'),
          rows: [
            _row(context.tr('period'), _periodLabel(_ownerDashboard!.period)),
            _row(context.tr('range'), '${_ownerDashboard!.startDate} -> ${_ownerDashboard!.endDate}'),
            _row(context.tr('units'), '${_ownerDashboard!.totalUnits}'),
            _row(context.tr('occupancy'), '${_ownerDashboard!.occupancyPercent.toStringAsFixed(2)}%'),
            _row(context.tr('revenue'), _ownerDashboard!.revenueTotal),
            _row(context.tr('collections'), _ownerDashboard!.collectionsTotal),
            _row(context.tr('outstanding'), _ownerDashboard!.outstandingTotal),
            _row(context.tr('net_income'), _ownerDashboard!.netIncomeTotal),
            _row(context.tr('maintenance_cost'), _ownerDashboard!.maintenanceTotalCost),
          ],
        ),
      );
      return cards;
    }

    cards.addAll([
      _ReportCard(
        title: context.tr('occupancy'),
        rows: [
          _row(context.tr('occupancy_percent'), '${_occupancy?.occupancyPercent.toStringAsFixed(2) ?? '0'}%'),
          _meter(
            value: ((_occupancy?.occupancyPercent ?? 0) / 100).clamp(0, 1),
            color: Colors.indigo,
          ),
          const SizedBox(height: 8),
          _row(context.tr('total_units'), '${_occupancy?.totalUnits ?? 0}'),
          _row(context.tr('booked_nights'), '${_occupancy?.bookedNights ?? 0}'),
          _row(context.tr('active_bookings'), '${_occupancy?.activeBookingsCount ?? 0}'),
        ],
      ),
      _ReportCard(
        title: context.tr('revenue'),
        rows: [
          _row(context.tr('revenue_total'), _revenue?.revenueTotal ?? '0'),
          _meter(
            value: _safeRatio(_revenue?.collectionsTotal, _revenue?.revenueTotal),
            color: Colors.green,
          ),
          const SizedBox(height: 8),
          _row(context.tr('collections'), _revenue?.collectionsTotal ?? '0'),
          _row(context.tr('outstanding'), _revenue?.outstandingTotal ?? '0'),
          _row(context.tr('tax'), _revenue?.taxTotal ?? '0'),
        ],
      ),
      _ReportCard(
        title: context.tr('aging'),
        rows: [
          _row(context.tr('total_outstanding'), _aging?.totalOutstanding ?? '0'),
          ...(_aging?.buckets ?? const []).map((b) {
            final total = double.tryParse(_aging?.totalOutstanding ?? '0') ?? 0;
            final amount = double.tryParse(b.amount) ?? 0;
            final ratio = total > 0 ? (amount / total).clamp(0, 1).toDouble() : 0.0;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _row('${b.label} (${b.count})', b.amount),
                _meter(value: ratio, color: Colors.deepOrange),
                const SizedBox(height: 8),
              ],
            );
          }),
        ],
      ),
    ]);

    return cards;
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Expanded(child: Text(label)),
          const SizedBox(width: 8),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }

  Widget _meter({
    required double value,
    required Color color,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: LinearProgressIndicator(
        minHeight: 10,
        value: value,
        valueColor: AlwaysStoppedAnimation<Color>(color),
        backgroundColor: color.withValues(alpha: 0.16),
      ),
    );
  }

  double _safeRatio(String? part, String? total) {
    final p = double.tryParse(part ?? '') ?? 0;
    final t = double.tryParse(total ?? '') ?? 0;
    if (t <= 0) return 0;
    return (p / t).clamp(0, 1);
  }
}

class _ReportCard extends StatelessWidget {
  final String title;
  final List<Widget> rows;

  const _ReportCard({
    required this.title,
    required this.rows,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              color: AppTheme.primaryNavy,
            ),
          ),
          const SizedBox(height: 10),
          ...rows,
        ],
      ),
    );
  }
}
