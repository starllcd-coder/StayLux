import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../localization/app_strings.dart';

class AppBottomNavShell extends StatelessWidget {
  final Widget child;

  const AppBottomNavShell({
    super.key,
    required this.child,
  });

  int _currentIndex(String location) {
    if (location.startsWith("/wishlist")) return 1;
    if (location.startsWith("/booking-history")) return 2;
    if (location.startsWith("/notifications")) return 3;
    if (location.startsWith("/profile")) return 4;
    return 0;
  }

  void _onTap(BuildContext context, int index) {
    switch (index) {
      case 0:
        context.go("/home");
        break;
      case 1:
        context.go("/wishlist");
        break;
      case 2:
        context.go("/booking-history");
        break;
      case 3:
        context.go("/notifications");
        break;
      case 4:
        context.go("/profile");
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final currentIndex = _currentIndex(location);

    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) => _onTap(context, index),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.home_outlined),
            selectedIcon: const Icon(Icons.home_rounded),
            label: "Home".tr(context),
          ),
          NavigationDestination(
            icon: const Icon(Icons.favorite_border_rounded),
            selectedIcon: const Icon(Icons.favorite_rounded),
            label: "Wishlist".tr(context),
          ),
          NavigationDestination(
            icon: const Icon(Icons.receipt_long_outlined),
            selectedIcon: const Icon(Icons.receipt_long_rounded),
            label: "Bookings".tr(context),
          ),
          NavigationDestination(
            icon: const Icon(Icons.notifications_none_rounded),
            selectedIcon: const Icon(Icons.notifications_rounded),
            label: "Alerts".tr(context),
          ),
          NavigationDestination(
            icon: const Icon(Icons.person_outline_rounded),
            selectedIcon: const Icon(Icons.person_rounded),
            label: "Profile".tr(context),
          ),
        ],
      ),
    );
  }
}
