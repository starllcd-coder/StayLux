import 'package:flutter/material.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/operations_models.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../auth/controllers/admin_session_controller.dart';
import '../../../dashboard/controllers/admin_dashboard_controller.dart';
import '../../../dashboard/controllers/selected_property_controller.dart';
import '../../../dashboard/presentation/widgets/admin_bottom_nav.dart';

class StaffPage extends StatefulWidget {
  const StaffPage({super.key});

  @override
  State<StaffPage> createState() => _StaffPageState();
}

class _StaffPageState extends State<StaffPage> {
  final AdminAccessController _access = AdminAccessController();
  final AdminSessionController _sessionController = AdminSessionController();
  final AdminDashboardController _controller = AdminDashboardController();
  final TextEditingController _searchController = TextEditingController();

  bool _isLoading = true;
  String? _error;
  String _activeFilter = 'all';
  String _sortBy = 'name_asc';
  List<StaffMemberItem> _all = const [];

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
      final data = await _controller.loadStaff(propertyId: propertyId);
      if (!mounted) return;
      setState(() => _all = data);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  List<StaffMemberItem> get _rows {
    final query = _searchController.text.trim().toLowerCase();

    final filtered = _all.where((item) {
      final activeOk = _activeFilter == 'all' ||
          (_activeFilter == 'active' && item.isActive) ||
          (_activeFilter == 'inactive' && !item.isActive);
      if (!activeOk) return false;

      if (query.isEmpty) return true;
      return item.name.toLowerCase().contains(query) || item.role.toLowerCase().contains(query);
    }).toList();

    switch (_sortBy) {
      case 'name_desc':
        filtered.sort((a, b) => b.name.compareTo(a.name));
        break;
      case 'role':
        filtered.sort((a, b) => a.role.compareTo(b.role));
        break;
      case 'name_asc':
      default:
        filtered.sort((a, b) => a.name.compareTo(b.name));
    }

    return filtered;
  }

  @override
  Widget build(BuildContext context) {
    final rows = _rows;

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('staff')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      backgroundColor: AppTheme.lightBg,
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/staff',
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
                      hintText: context.tr('search_staff_name_role'),
                      prefixIcon: Icon(Icons.search),
                      filled: true,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                DropdownButton<String>(
                  value: _activeFilter,
                  items: [
                    DropdownMenuItem(value: 'all', child: Text(context.tr('all'))),
                    DropdownMenuItem(value: 'active', child: Text(context.tr('active'))),
                    DropdownMenuItem(value: 'inactive', child: Text(context.tr('inactive'))),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() => _activeFilter = value);
                  },
                ),
                const SizedBox(width: 8),
                DropdownButton<String>(
                  value: _sortBy,
                  items: [
                    DropdownMenuItem(value: 'name_asc', child: Text(context.tr('name_a_z'))),
                    DropdownMenuItem(value: 'name_desc', child: Text(context.tr('name_z_a'))),
                    DropdownMenuItem(value: 'role', child: Text(context.tr('role'))),
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
            Expanded(child: _StateView(message: context.tr('failed_load_staff', params: {'error': '$_error'}), onRetry: _load)),
          if (!_isLoading && _error == null && rows.isEmpty)
            Expanded(child: _StateView(message: context.tr('no_matching_staff'))),
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
                          CircleAvatar(
                            backgroundColor: AppTheme.luxuryGold.withValues(alpha: 0.18),
                            child: Text(
                              (item.name.isEmpty ? '?' : item.name.substring(0, 1)).toUpperCase(),
                              style: const TextStyle(
                                color: AppTheme.primaryNavy,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(item.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                                const SizedBox(height: 4),
                                Text(item.role),
                                Text(item.isActive ? context.tr('active') : context.tr('inactive')),
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
