class AdminUser {
  final String id;
  final String name;
  final String email;
  final String role;
  final String backendRole;
  final List<String> propertyIds;
  final String token;
  final String refreshToken;

  const AdminUser({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    required this.backendRole,
    required this.propertyIds,
    required this.token,
    required this.refreshToken,
  });

  factory AdminUser.fromJson(Map<String, dynamic> json) {
    return AdminUser(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      email: json['email'] ?? '',
      role: json['role'] ?? 'staff',
      backendRole: json['backendRole'] ?? '',
      propertyIds: List<String>.from(json['propertyIds'] ?? const []),
      token: json['token'] ?? '',
      refreshToken: json['refreshToken'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'role': role,
      'backendRole': backendRole,
      'propertyIds': propertyIds,
      'token': token,
      'refreshToken': refreshToken,
    };
  }

  bool get isOwner => role == 'owner';
  bool get isManager => role == 'manager';
  bool get isStaff => role == 'staff';
}
