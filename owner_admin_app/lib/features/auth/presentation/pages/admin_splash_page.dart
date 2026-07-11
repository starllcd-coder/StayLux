import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../controllers/admin_session_controller.dart';
import '../../../../core/theme/app_theme.dart';

class AdminSplashPage extends StatefulWidget {
  const AdminSplashPage({super.key});

  @override
  State<AdminSplashPage> createState() => _AdminSplashPageState();
}

class _AdminSplashPageState extends State<AdminSplashPage> {
  final AdminSessionController _sessionController = AdminSessionController();

  @override
  void initState() {
    super.initState();
    _checkSession();
  }

  Future<void> _checkSession() async {
    final loggedIn = await _sessionController.checkLoggedIn();

    if (!mounted) return;

    if (loggedIn) {
      if (_sessionController.getCurrentBackendRole() == 'owner') {
        context.go('/admin/owner-dashboard');
      } else {
        context.go('/admin/dashboard');
      }
    } else {
      context.go('/admin/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: AppTheme.lightBg,
      body: Center(
        child: CircularProgressIndicator(),
      ),
    );
  }
}
