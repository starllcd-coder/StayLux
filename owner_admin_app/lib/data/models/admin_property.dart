class AdminProperty {
  final String id;
  final String name;
  final String city;

  const AdminProperty({
    required this.id,
    required this.name,
    required this.city,
  });

  factory AdminProperty.fromJson(Map<String, dynamic> json) {
    return AdminProperty(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      city: json['city'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'city': city,
    };
  }
}