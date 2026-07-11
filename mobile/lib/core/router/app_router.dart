import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/controllers/auth_controller.dart';
import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/auth/presentation/pages/register_page.dart';
import '../../features/booking/presentation/pages/booking_history_page.dart';
import '../../features/booking/presentation/pages/booking_page.dart';
import '../../features/booking/presentation/pages/booking_success_page.dart';
import '../../features/discovery/presentation/pages/home_page.dart';
import '../../features/notifications/presentation/pages/notifications_page.dart';
import '../../features/onboarding/presentation/pages/country_selection_page.dart';
import '../../features/profile/presentation/pages/profile_page.dart';
import '../../features/profile/presentation/pages/chat_page.dart';
import '../../features/profile/presentation/pages/concierge_page.dart';
import '../../features/profile/presentation/pages/membership_page.dart';
import '../../features/profile/presentation/pages/account_preferences_page.dart';
import '../../features/profile/presentation/pages/security_center_page.dart';
import '../../features/property/presentation/pages/property_details_page.dart';
import '../../features/reviews/presentation/pages/reviews_page.dart';
import '../../features/wishlist/presentation/pages/wishlist_page.dart';
import '../widgets/app_bottom_nav_shell.dart';
import '../utils/gcc_region.dart';
import '../region/app_region_controller.dart';

final goRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authControllerProvider);
  final regionState = ref.watch(appRegionProvider);

  return GoRouter(
    initialLocation: "/login",
    refreshListenable: GoRouterRefreshStream(
      ref.watch(authControllerProvider.notifier).stream,
    ),
    redirect: (context, state) {
      final isLoading = authState.status == AuthStatus.unknown;
      final isLoggedIn = authState.status == AuthStatus.authenticated;
      final hasCountry = regionState.hasRegion;

      final isAuthRoute =
          state.matchedLocation == "/login" || state.matchedLocation == "/register";
      final isCountryRoute = state.matchedLocation == "/select-country";

      if (isLoading) return null;
      if (!hasCountry && !isCountryRoute) {
        return "/select-country";
      }

      if (hasCountry && isCountryRoute) {
        return isLoggedIn ? "/home" : "/login";
      }

      if (!isLoggedIn && !isAuthRoute && !isCountryRoute) {
        return "/login";
      }

      if (isLoggedIn && isAuthRoute) {
        return "/home";
      }

      return null;
    },
    routes: [
      GoRoute(
        path: "/select-country",
        builder: (context, state) => const CountrySelectionPage(),
      ),
      GoRoute(
        path: "/login",
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: "/register",
        builder: (context, state) => const RegisterPage(),
      ),
      ShellRoute(
        builder: (context, state, child) {
          return AppBottomNavShell(child: child);
        },
        routes: [
          GoRoute(
            path: "/home",
            builder: (context, state) => const HomePage(),
          ),
          GoRoute(
            path: "/wishlist",
            builder: (context, state) => const WishlistPage(),
          ),
          GoRoute(
            path: "/booking-history",
            builder: (context, state) => const BookingHistoryPage(),
          ),
          GoRoute(
            path: "/notifications",
            builder: (context, state) => const NotificationsPage(),
          ),
          GoRoute(
            path: "/profile",
            builder: (context, state) => const ProfilePage(),
          ),
        ],
      ),
      GoRoute(
        path: "/property/:id",
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters["id"] ?? "") ?? 0;
          return PropertyDetailsPage(propertyId: id);
        },
      ),
      GoRoute(
        path: "/booking",
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>? ?? {};
          return BookingPage(
            unitId: extra["unitId"] ?? 0,
            propertyName: (extra["propertyName"] ?? "").toString(),
            unitCode: (extra["unitCode"] ?? "").toString(),
            propertyCountry: (extra["propertyCountry"] ?? "").toString(),
          );
        },
      ),
      GoRoute(
        path: "/booking-success",
        builder: (context, state) {
          final extra = state.extra as Map<String, dynamic>? ?? {};
          return BookingSuccessPage(
            propertyName: (extra["propertyName"] ?? "").toString(),
            unitCode: (extra["unitCode"] ?? "").toString(),
            bookingId: extra["bookingId"] ?? 0,
            paymentId: extra["paymentId"] ?? 0,
            total: (extra["total"] is num) ? (extra["total"] as num).toDouble() : 0.0,
            currency: (extra["currency"]?.toString().trim().isNotEmpty ?? false)
                ? extra["currency"].toString()
                : currencyForCountry(
                    (extra["propertyCountry"]?.toString().trim().isNotEmpty ?? false)
                        ? (extra["propertyCountry"] ?? "").toString()
                        : regionState.country,
                  ),
            paymentMethod: (extra["paymentMethod"] ?? "").toString(),
            propertyCountry: (extra["propertyCountry"] ?? "").toString(),
            appCountry: regionState.country,
          );
        },
      ),
      GoRoute(
        path: "/reviews/:propertyId",
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters["propertyId"] ?? "") ?? 0;
          return ReviewsPage(propertyId: id);
        },
      ),
      GoRoute(
        path: "/chat",
        builder: (context, state) => const ChatPage(),
      ),
      GoRoute(
        path: "/concierge",
        builder: (context, state) => const ConciergePage(),
      ),
      GoRoute(
        path: "/membership",
        builder: (context, state) => const MembershipPage(),
      ),
      GoRoute(
        path: "/security-center",
        builder: (context, state) => const SecurityCenterPage(),
      ),
      GoRoute(
        path: "/preferences",
        builder: (context, state) => const AccountPreferencesPage(),
      ),
    ],
  );
});

class GoRouterRefreshStream extends ChangeNotifier {
  GoRouterRefreshStream(Stream<dynamic> stream) {
    notifyListeners();
    _subscription = stream.asBroadcastStream().listen(
          (_) => notifyListeners(),
        );
  }

  late final StreamSubscription<dynamic> _subscription;

  @override
  void dispose() {
    _subscription.cancel();
    super.dispose();
  }
}
