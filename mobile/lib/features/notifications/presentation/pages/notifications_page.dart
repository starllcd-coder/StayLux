import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_empty_state.dart';
import '../../../../core/widgets/app_error_state.dart';
import '../../../../core/widgets/app_loader.dart';
import '../controllers/notification_controller.dart';

class NotificationsPage extends ConsumerStatefulWidget {
  const NotificationsPage({super.key});

  @override
  ConsumerState<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends ConsumerState<NotificationsPage> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(notificationControllerProvider.notifier).load());
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(notificationControllerProvider);

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      appBar: AppBar(
        backgroundColor: AppTheme.ivory,
        title: Text(
          "Notifications".tr(context),
          style: TextStyle(
            color: AppTheme.darkText,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: Builder(
        builder: (_) {
          if (state.isLoading) {
            return AppLoader(message: "Loading notifications...".tr(context));
          }

          if (state.error != null && state.notifications.isEmpty) {
            return AppErrorState(
              message: state.error,
              onRetry: () =>
                  ref.read(notificationControllerProvider.notifier).load(),
            );
          }

          if (state.notifications.isEmpty) {
            return AppEmptyState(
              icon: Icons.notifications_none_rounded,
              title: "No notifications yet".tr(context),
              message: "Booking updates and alerts will appear here.".tr(context),
            );
          }

          return RefreshIndicator(
            onRefresh: () =>
                ref.read(notificationControllerProvider.notifier).load(),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: state.notifications.length,
              itemBuilder: (context, index) {
                final item = state.notifications[index];
                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: item.isRead
                        ? Colors.white
                        : const Color(0xFFFFFAEE),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(
                      color: item.isRead
                          ? const Color(0xFFE8E1D2)
                          : const Color(0xFFF2D686),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        style: const TextStyle(
                          color: AppTheme.darkText,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        item.message,
                        style: const TextStyle(
                          color: AppTheme.darkText,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              item.createdAt,
                              style: const TextStyle(
                                color: AppTheme.mutedText,
                                fontSize: 12,
                              ),
                            ),
                          ),
                          if (!item.isRead)
                            TextButton(
                              onPressed: () => ref
                                  .read(notificationControllerProvider.notifier)
                                  .markAsRead(item.id),
                              child: Text("Mark as read".tr(context)),
                            ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
