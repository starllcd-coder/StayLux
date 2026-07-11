class AdminSession {
  final String token;
  final String role;
  final String userName;
  final String email;

  const AdminSession({
    required this.token,
    required this.role,
    required this.userName,
    required this.email,
  });

  factory AdminSession.fromJson(Map<String, dynamic> json) {
    return AdminSession(
      token: json['token'] ?? '',
      role: json['role'] ?? '',
      userName: json['userName'] ?? '',
      email: json['email'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'token': token,
      'role': role,
      'userName': userName,
      'email': email,
    };
  }
}