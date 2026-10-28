import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/repositories/token_storage.dart';

class AdminBottomNav extends StatelessWidget {
  final String currentRoute;
  final bool showStaffTab;
  final bool showSecurityTab;

  const AdminBottomNav({
    super.key,
    required this.currentRoute,
    required this.showStaffTab,
    required this.showSecurityTab,
  });

  List<_NavItem> _items() {
    final isOwner = TokenStorage.currentBackendRole == 'owner';

    if (isOwner) {
      return const [
        _NavItem('dashboard', Icons.dashboard_outlined, '/admin/owner-dashboard'),
        _NavItem('reports', Icons.bar_chart_outlined, '/admin/reports'),
        _NavItem('notify', Icons.notifications_outlined, '/admin/notifications'),
        _NavItem('settings', Icons.settings_outlined, '/admin/settings'),
      ];
    }

    if (TokenStorage.currentBackendRole == 'accounts') {
      return const [
        _NavItem('dashboard', Icons.dashboard_outlined, '/admin/dashboard'),
        _NavItem('reports', Icons.bar_chart_outlined, '/admin/reports'),
        _NavItem('notify', Icons.notifications_outlined, '/admin/notifications'),
        _NavItem('settings', Icons.settings_outlined, '/admin/settings'),
      ];
    }

    final items = <_NavItem>[
      const _NavItem('dashboard', Icons.dashboard_outlined, '/admin/dashboard'),
      const _NavItem('bookings', Icons.book_online_outlined, '/admin/reservations'),
      const _NavItem('cleaning', Icons.cleaning_services_outlined, '/admin/housekeeping'),
      const _NavItem('repairs', Icons.build_outlined, '/admin/maintenance'),
      const _NavItem('notify', Icons.notifications_outlined, '/admin/notifications'),
      const _NavItem('reports', Icons.bar_chart_outlined, '/admin/reports'),
    ];

    if (showSecurityTab) {
      items.add(const _NavItem('security', Icons.shield_outlined, '/admin/security'));
    }

    if (showStaffTab) {
      items.add(const _NavItem('staff', Icons.people_outline, '/admin/staff'));
    }

    items.add(const _NavItem('settings', Icons.settings_outlined, '/admin/settings'));

    return items;
  }

  @override
  Widget build(BuildContext context) {
    final items = _items();

    return Material(
      color: Colors.white,
      elevation: 8,
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 80,
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Row(
              children: items.map((item) {
                final isSelected = item.route == currentRoute;
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: () => context.go(item.route),
                    child: Container(
                      width: 90,
                      decoration: BoxDecoration(
                        color: isSelected
                            ? AppTheme.luxuryGold.withValues(alpha: 0.18)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            item.icon,
                            size: 22,
                            color: isSelected ? AppTheme.primaryNavy : Colors.black54,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            context.tr(item.label),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12,
                              color: isSelected ? AppTheme.primaryNavy : Colors.black87,
                              fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem {
  final String label;
  final IconData icon;
  final String route;

  const _NavItem(this.label, this.icon, this.route);
}
