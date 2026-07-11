class ReservationItem {
  final int id;
  final String guestLabel;
  final String unitLabel;
  final String status;
  final String stayLabel;
  final String startDate;
  final String endDate;
  final String bookingType;
  final String createdAt;
  final String updatedAt;

  const ReservationItem({
    required this.id,
    required this.guestLabel,
    required this.unitLabel,
    required this.status,
    required this.stayLabel,
    required this.startDate,
    required this.endDate,
    required this.bookingType,
    required this.createdAt,
    required this.updatedAt,
  });
}

class HousekeepingTaskItem {
  final int id;
  final String title;
  final String unitLabel;
  final String status;
  final String priority;
  final String assignedTo;
  final int? assignedToId;
  final String createdAt;
  final String updatedAt;
  final String completedAt;

  const HousekeepingTaskItem({
    required this.id,
    required this.title,
    required this.unitLabel,
    required this.status,
    required this.priority,
    required this.assignedTo,
    required this.assignedToId,
    required this.createdAt,
    required this.updatedAt,
    required this.completedAt,
  });
}

class MaintenanceItem {
  final int id;
  final String title;
  final String unitLabel;
  final String status;
  final String priority;
  final String assignedTo;
  final int? assignedToId;
  final String createdAt;
  final String updatedAt;
  final String resolvedAt;

  const MaintenanceItem({
    required this.id,
    required this.title,
    required this.unitLabel,
    required this.status,
    required this.priority,
    required this.assignedTo,
    required this.assignedToId,
    required this.createdAt,
    required this.updatedAt,
    required this.resolvedAt,
  });
}

class StaffMemberItem {
  final int id;
  final String name;
  final String role;
  final bool isActive;

  const StaffMemberItem({
    required this.id,
    required this.name,
    required this.role,
    required this.isActive,
  });
}

class SecurityAlertItem {
  final int id;
  final String title;
  final String channel;
  final String status;
  final String createdAt;
  final bool isRead;
  final String content;
  final String error;

  const SecurityAlertItem({
    required this.id,
    required this.title,
    required this.channel,
    required this.status,
    required this.createdAt,
    required this.isRead,
    required this.content,
    required this.error,
  });
}

class NotificationSettingItem {
  final int id;
  final String propertyProfile;
  final bool enableWhatsApp;
  final String defaultChannel;
  final String notes;

  const NotificationSettingItem({
    required this.id,
    required this.propertyProfile,
    required this.enableWhatsApp,
    required this.defaultChannel,
    required this.notes,
  });
}
