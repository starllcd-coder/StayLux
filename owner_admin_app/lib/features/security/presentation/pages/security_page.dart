import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/realtime/realtime_service.dart';
import '../../../../core/services/telemetry_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/operations_models.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../auth/controllers/admin_session_controller.dart';
import '../../../dashboard/controllers/admin_dashboard_controller.dart';
import '../../../dashboard/controllers/selected_property_controller.dart';
import '../../../dashboard/presentation/widgets/admin_bottom_nav.dart';

class SecurityPage extends StatefulWidget {
  final AdminAccessController? accessController;
  final AdminSessionController? sessionController;
  final AdminDashboardController? dashboardController;
  final RealtimeService? realtimeService;

  const SecurityPage({
    super.key,
    this.accessController,
    this.sessionController,
    this.dashboardController,
    this.realtimeService,
  });

  @override
  State<SecurityPage> createState() => _SecurityPageState();
}

class _SecurityPageState extends State<SecurityPage> {
  late final AdminAccessController _access;
  late final AdminSessionController _sessionController;
  late final AdminDashboardController _controller;
  late final RealtimeService _realtimeService;
  final TextEditingController _searchController = TextEditingController();
  StreamSubscription<DateTime>? _tickSubscription;

  bool _isLoading = true;
  String? _error;
  String _statusFilter = 'all';
  String _sortBy = 'id_desc';
  List<SecurityAlertItem> _all = const [];

  @override
  void initState() {
    super.initState();
    _access = widget.accessController ?? AdminAccessController();
    _sessionController = widget.sessionController ?? AdminSessionController();
    _controller = widget.dashboardController ?? AdminDashboardController();
    _realtimeService = widget.realtimeService ?? PollingRealtimeService();
    TelemetryService.instance.trackScreen('security');
    SelectedPropertyController.ensureDefault(_sessionController.getPropertyIds());
    _searchController.addListener(() => setState(() {}));
    _load();
    _tickSubscription = _realtimeService.ticks.listen((_) => _load(silent: true));
    _realtimeService.start();
  }

  @override
  void dispose() {
    _tickSubscription?.cancel();
    _realtimeService.dispose();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }
    try {
      final propertyId = SelectedPropertyController.selectedPropertyId;
      if (propertyId == null || propertyId.isEmpty) {
        throw Exception('No property selected');
      }
      final data = await _controller.loadSecurityAlerts(propertyId: propertyId);
      if (!mounted) return;
      setState(() => _all = data);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted && !silent) {
        setState(() => _isLoading = false);
      }
    }
  }

  List<SecurityAlertItem> get _rows {
    final query = _searchController.text.trim().toLowerCase();

    final filtered = _all.where((item) {
      final statusOk = _statusFilter == 'all' || item.status == _statusFilter;
      if (!statusOk) return false;

      if (query.isEmpty) return true;
      return item.title.toLowerCase().contains(query) ||
          item.channel.toLowerCase().contains(query) ||
          item.status.toLowerCase().contains(query);
    }).toList();

    switch (_sortBy) {
      case 'status':
        filtered.sort((a, b) => a.status.compareTo(b.status));
        break;
      case 'title':
        filtered.sort((a, b) => a.title.compareTo(b.title));
        break;
      case 'id_asc':
        filtered.sort((a, b) => a.id.compareTo(b.id));
        break;
      case 'id_desc':
      default:
        filtered.sort((a, b) => b.id.compareTo(a.id));
    }

    return filtered;
  }

  @override
  Widget build(BuildContext context) {
    final rows = _rows;

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('security')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      backgroundColor: AppTheme.lightBg,
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/security',
        showStaffTab: _access.canManageStaff(),
        showSecurityTab: _access.canManageSecurity(),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: context.tr('search_title_channel_status'),
                      prefixIcon: Icon(Icons.search),
                      filled: true,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                DropdownButton<String>(
                  value: _statusFilter,
                  items: [
                    DropdownMenuItem(value: 'all', child: Text(context.tr('all'))),
                    DropdownMenuItem(value: 'pending', child: Text(context.tr('pending'))),
                    DropdownMenuItem(value: 'sent', child: Text(context.tr('sent'))),
                    DropdownMenuItem(value: 'failed', child: Text(context.tr('failed'))),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() => _statusFilter = value);
                  },
                ),
                const SizedBox(width: 8),
                DropdownButton<String>(
                  value: _sortBy,
                  items: [
                    DropdownMenuItem(value: 'id_desc', child: Text(context.tr('newest'))),
                    DropdownMenuItem(value: 'id_asc', child: Text(context.tr('oldest'))),
                    DropdownMenuItem(value: 'status', child: Text(context.tr('status'))),
                    DropdownMenuItem(value: 'title', child: Text(context.tr('title'))),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() => _sortBy = value);
                  },
                ),
              ],
            ),
          ),
          if (_isLoading) const Expanded(child: Center(child: CircularProgressIndicator())),
          if (!_isLoading && _error != null)
            Expanded(child: _StateView(message: context.tr('failed_load_security', params: {'error': '$_error'}), onRetry: _load)),
          if (!_isLoading && _error == null && rows.isEmpty)
            Expanded(child: _StateView(message: context.tr('no_matching_security'))),
          if (!_isLoading && _error == null && rows.isNotEmpty)
            Expanded(
              child: RefreshIndicator(
                onRefresh: _load,
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: rows.length,
                  itemBuilder: (context, index) {
                    final item = rows[index];
                    return Container(
                      margin: const EdgeInsets.only(bottom: 14),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Row(
                        children: [
                          const CircleAvatar(
                            backgroundColor: Color(0xFFFFF3CD),
                            child: Icon(Icons.shield_outlined, color: Colors.orange),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(item.title, style: const TextStyle(fontWeight: FontWeight.w700)),
                                const SizedBox(height: 4),
                                Text(context.tr('channel_label', params: {'value': item.channel})),
                                Text(context.tr('status_label', params: {'value': context.tr(item.status)})),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _StateView extends StatelessWidget {
  final String message;
  final Future<void> Function()? onRetry;

  const _StateView({required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              FilledButton(onPressed: onRetry, child: Text(context.tr('retry'))),
            ],
          ],
        ),
      ),
    );
  }
}
