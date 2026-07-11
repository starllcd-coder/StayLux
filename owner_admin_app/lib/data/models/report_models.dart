class OccupancyReportModel {
  final int totalUnits;
  final int totalUnitNights;
  final int bookedNights;
  final double occupancyPercent;
  final int activeBookingsCount;

  const OccupancyReportModel({
    required this.totalUnits,
    required this.totalUnitNights,
    required this.bookedNights,
    required this.occupancyPercent,
    required this.activeBookingsCount,
  });
}

class RevenueReportModel {
  final String revenueTotal;
  final String taxTotal;
  final String outstandingTotal;
  final String collectionsTotal;

  const RevenueReportModel({
    required this.revenueTotal,
    required this.taxTotal,
    required this.outstandingTotal,
    required this.collectionsTotal,
  });
}

class AgingBucketModel {
  final String label;
  final int count;
  final String amount;

  const AgingBucketModel({
    required this.label,
    required this.count,
    required this.amount,
  });
}

class AgingReportModel {
  final String totalOutstanding;
  final List<AgingBucketModel> buckets;

  const AgingReportModel({
    required this.totalOutstanding,
    required this.buckets,
  });
}
