import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_empty_state.dart';
import '../../../../core/widgets/app_error_state.dart';
import '../../../../core/widgets/app_loader.dart';
import '../controllers/booking_controller.dart';
import '../widgets/booking_card.dart';

class BookingHistoryPage extends ConsumerStatefulWidget {
  const BookingHistoryPage({super.key});

  @override
  ConsumerState<BookingHistoryPage> createState() => _BookingHistoryPageState();
}

class _BookingHistoryPageState extends ConsumerState<BookingHistoryPage> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(bookingControllerProvider.notifier).loadMyBookings();
    });
  }

  Future<void> _cancelBooking(int bookingId) async {
    final ok = await ref.read(bookingControllerProvider.notifier).cancel(bookingId);
    if (!mounted) return;

    final state = ref.read(bookingControllerProvider);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          ok
              ? "Booking cancelled".tr(context)
              : (state.error ?? "Could not cancel booking".tr(context)),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(bookingControllerProvider);

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      appBar: AppBar(
        backgroundColor: AppTheme.ivory,
        title: Text(
          "My Bookings".tr(context),
          style: TextStyle(
            color: AppTheme.darkText,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: Builder(
        builder: (_) {
          if (state.isLoading) {
            return AppLoader(message: "Loading bookings...".tr(context));
          }

          if (state.error != null && state.bookings.isEmpty) {
            return AppErrorState(
              message: state.error,
              onRetry: () =>
                  ref.read(bookingControllerProvider.notifier).loadMyBookings(),
            );
          }

          if (state.bookings.isEmpty) {
            return AppEmptyState(
              icon: Icons.receipt_long_outlined,
              title: "No bookings found".tr(context),
              message: "Your confirmed and pending bookings will appear here."
                  .tr(context),
            );
          }

          return RefreshIndicator(
            onRefresh: () =>
                ref.read(bookingControllerProvider.notifier).loadMyBookings(),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: state.bookings.length,
              itemBuilder: (context, index) {
                final booking = state.bookings[index];
                return BookingCard(
                  booking: booking,
                  onCancel: () => _cancelBooking(booking.id),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
