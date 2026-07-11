import '../../domain/entities/user.dart';

class UserModel extends User {
  UserModel({
    required super.id,
    required super.email,
    required super.name,
    required super.mobile,
    required super.preferredLanguage,
    required super.preferredCountry,
    required super.isVerified,
    super.loyaltyPoints,
    super.loyaltyTier,
    super.referralCode,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json["id"] ?? 0,
      email: (json["email"] ?? "").toString(),
      name: (json["full_name"] ?? "").toString(),
      mobile: (json["mobile"] ?? "").toString(),
      preferredLanguage: (json["preferred_language"] ?? "en").toString(),
      preferredCountry: (json["preferred_country"] ?? "").toString(),
      isVerified: json["is_verified"] ?? false,
      loyaltyPoints: _toInt(json["loyalty_points"]),
      loyaltyTier: (json["loyalty_tier"] ?? "bronze").toString(),
      referralCode: (json["referral_code"] ?? "").toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      "id": id,
      "email": email,
      "full_name": name,
      "mobile": mobile,
      "preferred_language": preferredLanguage,
      "preferred_country": preferredCountry,
      "is_verified": isVerified,
      "loyalty_points": loyaltyPoints,
      "loyalty_tier": loyaltyTier,
      "referral_code": referralCode,
    };
  }

  static int _toInt(dynamic value) {
    if (value is int) return value;
    return int.tryParse((value ?? "0").toString()) ?? 0;
  }
}
