import 'package:flutter/material.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/operations_models.dart';

class ReservationDetailPage extends StatelessWidget {
  final ReservationItem item;

  const ReservationDetailPage({
    super.key,
    required this.item,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.lightBg,
      appBar: AppBar(
        title: Text(context.tr('reservation_details')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _DetailCard(
              title: context.tr('guest'),
              children: [
                _InfoRow(label: context.tr('name'), value: item.guestLabel),
                _InfoRow(label: context.tr('status'), value: context.tr(item.status)),
              ],
            ),
            const SizedBox(height: 12),
            _DetailCard(
              title: context.tr('stay'),
              children: [
                _InfoRow(label: context.tr('unit'), value: item.unitLabel),
                _InfoRow(label: context.tr('booking_type'), value: item.bookingType.isEmpty ? '-' : item.bookingType),
                _InfoRow(label: context.tr('start_date'), value: item.startDate.isEmpty ? '-' : item.startDate),
                _InfoRow(label: context.tr('end_date'), value: item.endDate.isEmpty ? '-' : item.endDate),
              ],
            ),
            const SizedBox(height: 12),
            _DetailCard(
              title: context.tr('timeline'),
              children: [
                _TimelineItem(
                  label: context.tr('reservation_created'),
                  done: true,
                  time: _formatTime(item.createdAt),
                ),
                _TimelineItem(
                  label: context.tr('last_updated'),
                  done: item.updatedAt.isNotEmpty,
                  time: _formatTime(item.updatedAt),
                ),
                _TimelineItem(
                  label: context.tr('guest_check_in'),
                  done: item.status == 'checked_in' || item.status == 'checked_out',
                ),
                _TimelineItem(
                  label: context.tr('guest_check_out'),
                  done: item.status == 'checked_out',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailCard extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _DetailCard({
    required this.title,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
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

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
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

class _TimelineItem extends StatelessWidget {
  final String label;
  final bool done;
  final String? time;

  const _TimelineItem({
    required this.label,
    required this.done,
    this.time,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Icon(
            done ? Icons.check_circle : Icons.radio_button_unchecked,
            color: done ? Colors.green : Colors.grey,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(time == null || time!.isEmpty ? label : '$label - $time'),
          ),
        ],
      ),
    );
  }
}

String _formatTime(String raw) {
  if (raw.trim().isEmpty) return '-';
  return raw.replaceFirst('T', ' ').split('.').first;
}
