class DashboardModel {
  final int occupancy;
  final int activeGuests;
  final int todayCheckIns;
  final int todayCheckOuts;
  final int openMaintenance;
  final int openHousekeeping;
  final int activeAlerts;
  final String revenueToday;
  final List<ActivityModel> recentActivities;

  const DashboardModel({
    required this.occupancy,
    required this.activeGuests,
    required this.todayCheckIns,
    required this.todayCheckOuts,
    required this.openMaintenance,
    required this.openHousekeeping,
    required this.activeAlerts,
    required this.revenueToday,
    required this.recentActivities,
  });

  factory DashboardModel.fromJson(Map<String, dynamic> json) {
    return DashboardModel(
      occupancy: json['occupancy'] ?? 0,
      activeGuests: json['activeGuests'] ?? 0,
      todayCheckIns: json['todayCheckIns'] ?? 0,
      todayCheckOuts: json['todayCheckOuts'] ?? 0,
      openMaintenance: json['openMaintenance'] ?? 0,
      openHousekeeping: json['openHousekeeping'] ?? 0,
      activeAlerts: json['activeAlerts'] ?? 0,
      revenueToday: json['revenueToday'] ?? '\$0',
      recentActivities: (json['recentActivities'] as List<dynamic>? ?? [])
          .map((e) => ActivityModel.fromJson(e))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'occupancy': occupancy,
      'activeGuests': activeGuests,
      'todayCheckIns': todayCheckIns,
      'todayCheckOuts': todayCheckOuts,
      'openMaintenance': openMaintenance,
      'openHousekeeping': openHousekeeping,
      'activeAlerts': activeAlerts,
      'revenueToday': revenueToday,
      'recentActivities': recentActivities.map((e) => e.toJson()).toList(),
    };
  }
}

class ActivityModel {
  final String title;
  final String subtitle;

  const ActivityModel({
    required this.title,
    required this.subtitle,
  });

  factory ActivityModel.fromJson(Map<String, dynamic> json) {
    return ActivityModel(
      title: json['title'] ?? '',
      subtitle: json['subtitle'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'subtitle': subtitle,
    };
  }
}