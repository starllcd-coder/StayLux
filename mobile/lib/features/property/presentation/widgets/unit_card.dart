import 'package:flutter/material.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/theme/app_theme.dart';
import '../../domain/entities/unit.dart';

class UnitCard extends StatelessWidget {
  final Unit unit;

  const UnitCard({
    super.key,
    required this.unit,
  });

  Color _statusBg(String status) {
    switch (status.toLowerCase()) {
      case "available":
        return const Color(0xFFEAF7EE);
      case "occupied":
        return const Color(0xFFFFEFEF);
      default:
        return const Color(0xFFF4F1E8);
    }
  }

  Color _statusText(String status) {
    switch (status.toLowerCase()) {
      case "available":
        return Colors.green;
      case "occupied":
        return Colors.redAccent;
      default:
        return AppTheme.primaryNavy;
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasNightlyPrice = unit.nightlyPrice != null;
    final hasEstimate = unit.estimatedTotal != null && unit.estimatedTotal! > 0;
    final normalizedStatus = unit.status.trim().isEmpty ? "unknown" : unit.status.trim().toLowerCase();
    final categoryText = unit.category.trim().isEmpty
        ? "Standard Unit".tr(context)
        : unit.category.replaceAll("_", " ").tr(context);
    final bedText = unit.bedConfig.isEmpty ? "N/A" : unit.bedConfig.replaceAll("_", " ");

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFEAE5DA)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.meeting_room_outlined,
                color: AppTheme.primaryNavy,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  unit.code.isEmpty ? "Unit".tr(context) : unit.code,
                  style: const TextStyle(
                    color: AppTheme.darkText,
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: _statusBg(unit.status),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  normalizedStatus.tr(context),
                  style: TextStyle(
                    color: _statusText(unit.status),
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            categoryText,
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            "${"Bed".tr(context)}: $bedText - ${"Guests".tr(context)}: ${unit.guestCapacity}",
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 12),
          if (hasNightlyPrice)
            Text(
              "${unit.currency} ${unit.nightlyPrice!.toStringAsFixed(0)} / ${"night".tr(context)}",
              style: const TextStyle(
                color: AppTheme.primaryNavy,
                fontWeight: FontWeight.w800,
                fontSize: 15,
              ),
            )
          else
            Text(
              "Rate unavailable".tr(context),
              style: const TextStyle(
                color: AppTheme.mutedText,
                fontSize: 14,
              ),
            ),
          if (hasEstimate) ...[
            const SizedBox(height: 6),
            Text(
              "${"Estimated total".tr(context)}: ${unit.currency} ${unit.estimatedTotal!.toStringAsFixed(2)}",
              style: const TextStyle(
                color: AppTheme.darkText,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
