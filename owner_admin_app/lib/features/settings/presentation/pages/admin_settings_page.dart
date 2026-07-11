import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/services/telemetry_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../auth/controllers/admin_auth_controller.dart';
import '../../../auth/controllers/admin_session_controller.dart';
import '../../../dashboard/controllers/selected_property_controller.dart';
import '../../../dashboard/presentation/widgets/admin_bottom_nav.dart';

class AdminSettingsPage extends StatefulWidget {
  final AdminSessionController? sessionController;
  final AdminAuthController? authController;

  const AdminSettingsPage({
    super.key,
    this.sessionController,
    this.authController,
  });

  @override
  State<AdminSettingsPage> createState() => _AdminSettingsPageState();
}

class _AdminSettingsPageState extends State<AdminSettingsPage> {
  late final AdminSessionController _sessionController;
  late final AdminAuthController _authController;
  late final AdminAccessController _accessController;
  bool _isLoggingOut = false;

  @override
  void initState() {
    super.initState();
    _sessionController = widget.sessionController ?? AdminSessionController();
    _authController = widget.authController ?? AdminAuthController();
    _accessController = AdminAccessController();
    TelemetryService.instance.trackScreen('settings');
  }

  Future<void> _logout() async {
    setState(() => _isLoggingOut = true);
    try {
      await _authController.logout();
      SelectedPropertyController.clear();
      if (!mounted) return;
      context.go('/admin/login');
    } finally {
      if (mounted) {
        setState(() => _isLoggingOut = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final userName = _sessionController.getCurrentUserName() ?? '-';
    final email = _sessionController.getCurrentEmail() ?? '-';
    final role = _sessionController.getCurrentRole() ?? '-';
    final backendRole = _sessionController.getCurrentBackendRole() ?? '-';
    final userId = _sessionController.getCurrentUserId() ?? '-';
    final properties = _sessionController.getPropertyIds();

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('settings')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      backgroundColor: AppTheme.lightBg,
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/settings',
        showStaffTab: _accessController.canManageStaff(),
        showSecurityTab: _accessController.canManageSecurity(),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _Card(
            title: context.tr('settings_profile'),
            children: [
              _row(context.tr('name'), userName),
              _row(context.tr('email'), email),
              _row(context.tr('role'), role.toUpperCase()),
              _row(context.tr('backend_role'), backendRole),
              _row(context.tr('user_id'), userId),
            ],
          ),
          const SizedBox(height: 12),
          _Card(
            title: context.tr('settings_access'),
            children: [
              _row(context.tr('properties'), properties.isEmpty ? context.tr('none') : properties.join(', ')),
            ],
          ),
          const SizedBox(height: 12),
          _Card(
            title: context.tr('settings_environment'),
            children: [
              _row(context.tr('api_base_url'), AppConfig.apiBaseUrl),
            ],
          ),
          const SizedBox(height: 12),
          _Card(
            title: context.tr('settings_session'),
            children: [
              FilledButton(
                onPressed: _isLoggingOut ? null : _logout,
                child: Text(_isLoggingOut ? context.tr('logging_out') : context.tr('logout')),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: TextStyle(color: Colors.grey.shade700),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _Card extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _Card({
    required this.title,
    required this.children,
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
          ...children,
        ],
      ),
    );
  }
}
