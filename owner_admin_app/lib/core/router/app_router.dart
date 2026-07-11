import 'package:go_router/go_router.dart';

import '../../data/repositories/token_storage.dart';
import '../../features/auth/controllers/admin_route_access_controller.dart';
import '../../features/auth/presentation/pages/access_denied_page.dart';
import '../../features/auth/presentation/pages/admin_login_page.dart';
import '../../features/auth/presentation/pages/admin_splash_page.dart';
import '../../features/dashboard/presentation/pages/admin_dashboard_page.dart';
import '../../features/housekeeping/presentation/pages/housekeeping_page.dart';
import '../../features/maintenance/presentation/pages/maintenance_page.dart';
import '../../features/notifications/presentation/pages/notifications_page.dart';
import '../../features/owner/presentation/pages/owner_dashboard_page.dart';
import '../../features/reports/presentation/pages/reports_page.dart';
import '../../features/reservations/presentation/pages/reservations_page.dart';
import '../../features/security/presentation/pages/security_page.dart';
import '../../features/settings/presentation/pages/admin_settings_page.dart';
import '../../features/staff/presentation/pages/staff_page.dart';

final appRouter = GoRouter(
  initialLocation: '/admin/splash',
  redirect: (context, state) {
    final token = TokenStorage.currentToken;
    final path = state.matchedLocation;
    final isOwner = TokenStorage.currentBackendRole == 'owner';
    const ownerAllowedRoutes = <String>{
      '/admin/owner-dashboard',
      '/admin/reports',
      '/admin/notifications',
      '/admin/settings',
    };

    final isLogin = path == '/admin/login';
    final isSplash = path == '/admin/splash';
    final isDenied = path == '/admin/access-denied';

    if ((token == null || token.isEmpty) && !isLogin && !isSplash) {
      return '/admin/login';
    }

    if (token != null && token.isNotEmpty && isLogin) {
      if (TokenStorage.currentBackendRole == 'owner') {
        return '/admin/owner-dashboard';
      }
      return '/admin/dashboard';
    }

    if (token != null && token.isNotEmpty && isOwner) {
      if (path == '/admin/dashboard') {
        return '/admin/owner-dashboard';
      }
      if (!isSplash &&
          !isLogin &&
          !isDenied &&
          !ownerAllowedRoutes.contains(path)) {
        return '/admin/owner-dashboard';
      }
    }

    if (token != null &&
        token.isNotEmpty &&
        !isSplash &&
        !isLogin &&
        !isDenied) {
      final access = AdminRouteAccessController();
      if (!access.canOpenRoute(path)) {
        return '/admin/access-denied';
      }
    }

    return null;
  },
  routes: [
    GoRoute(
      path: '/admin/splash',
      builder: (context, state) => const AdminSplashPage(),
    ),
    GoRoute(
      path: '/admin/login',
      builder: (context, state) => const AdminLoginPage(),
    ),
    GoRoute(
      path: '/admin/access-denied',
      builder: (context, state) => const AccessDeniedPage(),
    ),
    GoRoute(
      path: '/admin/dashboard',
      builder: (context, state) => const AdminDashboardPage(),
    ),
    GoRoute(
      path: '/admin/owner-dashboard',
      builder: (context, state) => const OwnerDashboardPage(),
    ),
    GoRoute(
      path: '/admin/reservations',
      builder: (context, state) => const ReservationsPage(),
    ),
    GoRoute(
      path: '/admin/housekeeping',
      builder: (context, state) => const HousekeepingPage(),
    ),
    GoRoute(
      path: '/admin/maintenance',
      builder: (context, state) => const MaintenancePage(),
    ),
    GoRoute(
      path: '/admin/security',
      builder: (context, state) => const SecurityPage(),
    ),
    GoRoute(
      path: '/admin/notifications',
      builder: (context, state) => const NotificationsPage(),
    ),
    GoRoute(
      path: '/admin/reports',
      builder: (context, state) => const ReportsPage(),
    ),
    GoRoute(
      path: '/admin/staff',
      builder: (context, state) => const StaffPage(),
    ),
    GoRoute(
      path: '/admin/settings',
      builder: (context, state) => const AdminSettingsPage(),
    ),
  ],
);
