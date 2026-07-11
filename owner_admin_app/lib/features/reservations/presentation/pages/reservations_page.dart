import 'package:flutter/material.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/operations_models.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../auth/controllers/admin_session_controller.dart';
import '../../../dashboard/controllers/admin_dashboard_controller.dart';
import '../../../dashboard/controllers/selected_property_controller.dart';
import '../../../dashboard/presentation/widgets/admin_bottom_nav.dart';
import 'reservation_detail_page.dart';

class ReservationsPage extends StatefulWidget {
  const ReservationsPage({super.key});

  @override
  State<ReservationsPage> createState() => _ReservationsPageState();
}

class _ReservationsPageState extends State<ReservationsPage> {
  final AdminAccessController _access = AdminAccessController();
  final AdminSessionController _sessionController = AdminSessionController();
  final AdminDashboardController _controller = AdminDashboardController();

  final TextEditingController _searchController = TextEditingController();

  bool _isLoading = true;
  bool _isRunningAction = false;
  String? _error;
  String _statusFilter = 'all';
  String _sortBy = 'id_desc';
  List<ReservationItem> _allReservations = const [];

  @override
  void initState() {
    super.initState();
    SelectedPropertyController.ensureDefault(_sessionController.getPropertyIds());
    _searchController.addListener(() => setState(() {}));
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final propertyId = SelectedPropertyController.selectedPropertyId;
      if (propertyId == null || propertyId.isEmpty) {
        throw Exception('No property selected');
      }

      final data = await _controller.loadReservations(propertyId: propertyId);
      if (!mounted) return;
      setState(() {
        _allReservations = data;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _runAction(Future<void> Function() action) async {
    setState(() => _isRunningAction = true);
    try {
      await action();
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('action_failed', params: {'error': '$e'}))),
      );
    } finally {
      if (mounted) {
        setState(() => _isRunningAction = false);
      }
    }
  }

  List<ReservationItem> get _filteredAndSorted {
    final query = _searchController.text.trim().toLowerCase();

    final filtered = _allReservations.where((item) {
      final statusOk = _statusFilter == 'all' || item.status == _statusFilter;
      if (!statusOk) return false;

      if (query.isEmpty) return true;
      return item.guestLabel.toLowerCase().contains(query) ||
          item.unitLabel.toLowerCase().contains(query) ||
          item.status.toLowerCase().contains(query);
    }).toList();

    switch (_sortBy) {
      case 'guest_asc':
        filtered.sort((a, b) => a.guestLabel.compareTo(b.guestLabel));
        break;
      case 'guest_desc':
        filtered.sort((a, b) => b.guestLabel.compareTo(a.guestLabel));
        break;
      case 'status_asc':
        filtered.sort((a, b) => a.status.compareTo(b.status));
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
    final rows = _filteredAndSorted;

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('reservations')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      backgroundColor: AppTheme.lightBg,
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/reservations',
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
                      hintText: context.tr('search_guest_unit_status'),
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
                    DropdownMenuItem(value: 'reserved', child: Text(context.tr('reserved'))),
                    DropdownMenuItem(value: 'checked_in', child: Text(context.tr('checked_in'))),
                    DropdownMenuItem(value: 'checked_out', child: Text(context.tr('checked_out'))),
                    DropdownMenuItem(value: 'cancelled', child: Text(context.tr('cancelled'))),
                    DropdownMenuItem(value: 'no_show', child: Text(context.tr('no_show'))),
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
                    DropdownMenuItem(value: 'guest_asc', child: Text(context.tr('guest_a_z'))),
                    DropdownMenuItem(value: 'guest_desc', child: Text(context.tr('guest_z_a'))),
                    DropdownMenuItem(value: 'status_asc', child: Text(context.tr('status'))),
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
            Expanded(
              child: _ErrorState(
                message: context.tr('failed_load_reservations', params: {'error': '$_error'}),
                onRetry: _load,
              ),
            ),
          if (!_isLoading && _error == null && rows.isEmpty)
            Expanded(
              child: _EmptyState(message: context.tr('no_matching_reservations')),
            ),
          if (!_isLoading && _error == null && rows.isNotEmpty)
            Expanded(
              child: RefreshIndicator(
                onRefresh: _load,
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: rows.length,
                  itemBuilder: (context, index) {
                    final item = rows[index];
                    return _ReservationCard(
                      item: item,
                      runningAction: _isRunningAction,
                      onCheckIn: item.status == 'reserved'
                          ? () => _runAction(() => _controller.checkInReservation(item.id))
                          : null,
                      onCheckOut: item.status == 'checked_in'
                          ? () => _runAction(() => _controller.checkOutReservation(item.id))
                          : null,
                      onCancel: (item.status == 'reserved' || item.status == 'checked_in')
                          ? () => _runAction(() => _controller.cancelReservation(item.id))
                          : null,
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

class _ReservationCard extends StatelessWidget {
  final ReservationItem item;
  final bool runningAction;
  final VoidCallback? onCheckIn;
  final VoidCallback? onCheckOut;
  final VoidCallback? onCancel;

  const _ReservationCard({
    required this.item,
    required this.runningAction,
    required this.onCheckIn,
    required this.onCheckOut,
    required this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    Color statusColor() {
      switch (item.status) {
        case 'checked_in':
          return Colors.green;
        case 'reserved':
          return Colors.blue;
        case 'checked_out':
          return Colors.grey;
        case 'cancelled':
        case 'no_show':
          return Colors.red;
        default:
          return Colors.blueGrey;
      }
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                backgroundColor: AppTheme.luxuryGold.withValues(alpha: 0.15),
                child: const Icon(Icons.person_outline, color: AppTheme.primaryNavy),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.guestLabel, style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(context.tr('unit_label', params: {'value': item.unitLabel})),
                    Text(item.stayLabel),
                    Chip(
                      label: Text(context.tr(item.status)),
                      backgroundColor: statusColor().withValues(alpha: 0.12),
                      labelStyle: TextStyle(color: statusColor()),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ReservationDetailPage(item: item),
                    ),
                  );
                },
                child: Text(context.tr('details')),
              ),
              OutlinedButton(
                onPressed: runningAction ? null : onCheckIn,
                child: Text(context.tr('check_in')),
              ),
              OutlinedButton(
                onPressed: runningAction ? null : onCheckOut,
                child: Text(context.tr('check_out')),
              ),
              OutlinedButton(
                onPressed: runningAction ? null : onCancel,
                child: Text(context.tr('cancel')),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final Future<void> Function() onRetry;

  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: onRetry, child: Text(context.tr('retry'))),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final String message;

  const _EmptyState({required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(message, textAlign: TextAlign.center),
      ),
    );
  }
}
