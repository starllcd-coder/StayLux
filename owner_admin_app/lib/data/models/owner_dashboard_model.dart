class OwnerDashboardModel {
  final String propertyProfile;
  final String period;
  final String startDate;
  final String endDate;
  final int totalUnits;
  final double occupancyPercent;
  final String revenueTotal;
  final String collectionsTotal;
  final String outstandingTotal;
  final String netIncomeTotal;
  final int pendingHousekeeping;
  final int openMaintenance;
  final String maintenanceTotalCost;

  const OwnerDashboardModel({
    required this.propertyProfile,
    required this.period,
    required this.startDate,
    required this.endDate,
    required this.totalUnits,
    required this.occupancyPercent,
    required this.revenueTotal,
    required this.collectionsTotal,
    required this.outstandingTotal,
    required this.netIncomeTotal,
    required this.pendingHousekeeping,
    required this.openMaintenance,
    required this.maintenanceTotalCost,
  });
}
