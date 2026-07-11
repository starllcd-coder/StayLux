import 'package:flutter/material.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/operations_models.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../auth/controllers/admin_session_controller.dart';
import '../../../dashboard/controllers/admin_dashboard_controller.dart';
import '../../../dashboard/controllers/selected_property_controller.dart';
import '../../../dashboard/presentation/widgets/admin_bottom_nav.dart';

class HousekeepingPage extends StatefulWidget {
  const HousekeepingPage({super.key});

  @override
  State<HousekeepingPage> createState() => _HousekeepingPageState();
}

class _HousekeepingPageState extends State<HousekeepingPage> {
  final AdminAccessController _access = AdminAccessController();
  final AdminSessionController _sessionController = AdminSessionController();
  final AdminDashboardController _controller = AdminDashboardController();
  final TextEditingController _searchController = TextEditingController();

  bool _isLoading = true;
  bool _isRunningAction = false;
  String? _error;
  String _statusFilter = 'all';
  final String _sortBy = 'id_desc';
  List<HousekeepingTaskItem> _all = const [];
  List<StaffMemberItem> _staff = const [];
  final Map<int, int?> _selectedAssignees = {};

  @override
  void initState() {
    super.initState();
    SelectedPropertyController.ensureDefault(
      _sessionController.getPropertyIds(),
    );
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

      final results = await Future.wait([
        _controller.loadHousekeeping(propertyId: propertyId),
        _controller.loadStaff(propertyId: propertyId),
      ]);

      if (!mounted) return;
      final tasks = results[0] as List<HousekeepingTaskItem>;
      final staff = results[1] as List<StaffMemberItem>;

      final selected = <int, int?>{};
      for (final task in tasks) {
        selected[task.id] = task.assignedToId;
      }

      setState(() {
        _all = tasks;
        _staff = staff.where((s) => s.isActive).toList();
        _selectedAssignees
          ..clear()
          ..addAll(selected);
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

  Future<void> _updateStatus(int id, String status) async {
    setState(() => _isRunningAction = true);
    try {
      await _controller.updateHousekeepingStatus(taskId: id, status: status);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(
        SnackBar(content: Text(context.tr('action_failed', params: {'error': '$e'}))),
      );
    } finally {
      if (mounted) {
        setState(() => _isRunningAction = false);
      }
    }
  }

  Future<void> _assignTask(int taskId) async {
    final selectedStaffId = _selectedAssignees[taskId];
    if (selectedStaffId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('select_staff_member_first'))),
      );
      return;
    }

    setState(() => _isRunningAction = true);
    try {
      await _controller.assignHousekeepingTask(
        taskId: taskId,
        staffId: selectedStaffId,
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(
        SnackBar(content: Text(context.tr('assign_failed', params: {'error': '$e'}))),
      );
    } finally {
      if (mounted) {
        setState(() => _isRunningAction = false);
      }
    }
  }

  List<HousekeepingTaskItem> get _rows {
    final query = _searchController.text.trim().toLowerCase();

    final filtered = _all.where((item) {
      final statusOk = _statusFilter == 'all' || item.status == _statusFilter;
      if (!statusOk) return false;

      if (query.isEmpty) return true;
      return item.title.toLowerCase().contains(query) ||
          item.unitLabel.toLowerCase().contains(query) ||
          item.assignedTo.toLowerCase().contains(query);
    }).toList();

    switch (_sortBy) {
      case 'priority':
        filtered.sort((a, b) => a.priority.compareTo(b.priority));
        break;
      case 'status':
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

  Color _statusColor(String status) {
    switch (status) {
      case 'done':
        return Colors.green;
      case 'in_progress':
        return Colors.orange;
      case 'cancelled':
        return Colors.red;
      default:
        return Colors.blueGrey;
    }
  }

  Color _priorityColor(String priority) {
    switch (priority) {
      case 'high':
        return Colors.red;
      case 'urgent':
        return Colors.deepOrange;
      default:
        return Colors.blue;
    }
  }

  String _staffNameById(int? id, String fallback) {
    if (id == null) return fallback;
    final found = _staff.where((s) => s.id == id).toList();
    if (found.isEmpty) return fallback;
    return found.first.name;
  }

  @override
  Widget build(BuildContext context) {
    final rows = _rows;

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('housekeeping')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      backgroundColor: AppTheme.lightBg,
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/housekeeping',
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
                      hintText: context.tr('search_title_unit_assignee'),
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
                    DropdownMenuItem(
                      value: 'in_progress',
                      child: Text(context.tr('in_progress')),
                    ),
                    DropdownMenuItem(value: 'done', child: Text(context.tr('done'))),
                    DropdownMenuItem(
                      value: 'cancelled',
                      child: Text(context.tr('cancelled')),
                    ),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() => _statusFilter = value);
                  },
                ),
              ],
            ),
          ),
          if (_isLoading)
            const Expanded(child: Center(child: CircularProgressIndicator())),
          if (!_isLoading && _error != null)
            Expanded(
              child: _StateView(
                message: context.tr('failed_load_housekeeping', params: {'error': '$_error'}),
                onRetry: _load,
              ),
            ),
          if (!_isLoading && _error == null && rows.isEmpty)
            Expanded(
              child: _StateView(message: context.tr('no_matching_housekeeping')),
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
                    final currentAssigned = _selectedAssignees[item.id];

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
                          Text(
                            item.title,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              color: AppTheme.primaryNavy,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              Chip(
                                label: Text(
                                  context.tr('unit_label', params: {'value': item.unitLabel}),
                                ),
                              ),
                              Chip(
                                label: Text(item.status),
                                backgroundColor: _statusColor(
                                  item.status,
                                ).withValues(alpha: 0.12),
                                labelStyle: TextStyle(
                                  color: _statusColor(item.status),
                                ),
                              ),
                              Chip(
                                label: Text(item.priority),
                                backgroundColor: _priorityColor(
                                  item.priority,
                                ).withValues(alpha: 0.12),
                                labelStyle: TextStyle(
                                  color: _priorityColor(item.priority),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            context.tr(
                              'assigned_to',
                              params: {
                                'name': _staffNameById(item.assignedToId, item.assignedTo),
                              },
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: DropdownButtonFormField<int>(
                                  initialValue: currentAssigned,
                                  isExpanded: true,
                                  hint: Text(context.tr('select_assignee')),
                                  items: _staff
                                      .map(
                                        (s) => DropdownMenuItem<int>(
                                          value: s.id,
                                          child: Text(s.name),
                                        ),
                                      )
                                      .toList(),
                                  onChanged: (value) {
                                    setState(() {
                                      _selectedAssignees[item.id] = value;
                                    });
                                  },
                                ),
                              ),
                              const SizedBox(width: 8),
                              FilledButton(
                                onPressed: _isRunningAction
                                    ? null
                                    : () => _assignTask(item.id),
                                child: Text(context.tr('assign')),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              OutlinedButton(
                                onPressed:
                                    (_isRunningAction ||
                                        item.status == 'pending')
                                    ? null
                                    : () => _updateStatus(item.id, 'pending'),
                                child: Text(context.tr('set_pending')),
                              ),
                              OutlinedButton(
                                onPressed:
                                    (_isRunningAction ||
                                        item.status == 'in_progress')
                                    ? null
                                    : () =>
                                          _updateStatus(item.id, 'in_progress'),
                                child: Text(context.tr('set_in_progress')),
                              ),
                              OutlinedButton(
                                onPressed:
                                    (_isRunningAction || item.status == 'done')
                                    ? null
                                    : () => _updateStatus(item.id, 'done'),
                                child: Text(context.tr('mark_done')),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          _TaskTimeline(
                            items: [
                              _TimelinePoint(
                                label: 'Task Created',
                                done: true,
                                time: _formatTime(item.createdAt),
                              ),
                              _TimelinePoint(
                                label: 'Assigned',
                                done: item.assignedToId != null,
                                time: item.assignedToId != null
                                    ? _formatTime(item.updatedAt)
                                    : null,
                              ),
                              _TimelinePoint(
                                label: 'In Progress',
                                done:
                                    item.status == 'in_progress' ||
                                    item.status == 'done',
                                time:
                                    (item.status == 'in_progress' ||
                                        item.status == 'done')
                                    ? _formatTime(item.updatedAt)
                                    : null,
                              ),
                              _TimelinePoint(
                                label: 'Completed',
                                done: item.status == 'done',
                                time: item.status == 'done'
                                    ? _formatTime(item.completedAt)
                                    : null,
                              ),
                            ],
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

class _TimelinePoint {
  final String label;
  final bool done;
  final String? time;

  const _TimelinePoint({required this.label, required this.done, this.time});
}

class _TaskTimeline extends StatelessWidget {
  final List<_TimelinePoint> items;

  const _TaskTimeline({required this.items});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFD),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Wrap(
        spacing: 10,
        runSpacing: 8,
        children: items
            .map(
              (item) => Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    item.done
                        ? Icons.check_circle
                        : Icons.radio_button_unchecked,
                    size: 16,
                    color: item.done ? Colors.green : Colors.grey,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    item.time == null || item.time!.isEmpty
                        ? item.label
                        : '${item.label} - ${item.time}',
                  ),
                ],
              ),
            )
            .toList(),
      ),
    );
  }
}

String _formatTime(String raw) {
  if (raw.trim().isEmpty) return '';
  return raw.replaceFirst('T', ' ').split('.').first;
}
