import '../../domain/entities/profile.dart';

class TravelerProfileModel extends TravelerProfile {
  TravelerProfileModel({
    required super.id,
    required super.fullName,
    required super.phone,
    required super.whatsapp,
    required super.email,
    required super.nationality,
    required super.idType,
    required super.idNumber,
    required super.idExpiry,
    required super.address,
    required super.notes,
    required super.isDefault,
    required super.isActive,
  });

  factory TravelerProfileModel.fromJson(Map<String, dynamic> json) {
    return TravelerProfileModel(
      id: json["id"] ?? 0,
      fullName: (json["full_name"] ?? "").toString(),
      phone: (json["phone"] ?? "").toString(),
      whatsapp: (json["whatsapp"] ?? "").toString(),
      email: (json["email"] ?? "").toString(),
      nationality: (json["nationality"] ?? "").toString(),
      idType: (json["id_type"] ?? "").toString(),
      idNumber: (json["id_number"] ?? "").toString(),
      idExpiry: (json["id_expiry"] ?? "").toString(),
      address: (json["address"] ?? "").toString(),
      notes: (json["notes"] ?? "").toString(),
      isDefault: json["is_default"] ?? false,
      isActive: json["is_active"] ?? true,
    );
  }
}

class CustomerProfileModel extends CustomerProfile {
  CustomerProfileModel({
    required super.id,
    required super.fullName,
    required super.email,
    required super.mobile,
    required super.preferredLanguage,
    required super.preferredCountry,
    required super.isVerified,
    super.loyaltyPoints,
    super.loyaltyTier,
    super.referralCode,
    required super.travelers,
  });

  factory CustomerProfileModel.fromJson(Map<String, dynamic> json) {
    final customer = (json["customer"] ?? {}) as Map<String, dynamic>;
    final travelersRaw = (json["travelers"] ?? []) as List;

    return CustomerProfileModel(
      id: customer["id"] ?? 0,
      fullName: (customer["full_name"] ?? "").toString(),
      email: (customer["email"] ?? "").toString(),
      mobile: (customer["mobile"] ?? "").toString(),
      preferredLanguage: (customer["preferred_language"] ?? "").toString(),
      preferredCountry: (customer["preferred_country"] ?? "").toString(),
      isVerified: customer["is_verified"] ?? false,
      loyaltyPoints: _toInt(customer["loyalty_points"]),
      loyaltyTier: (customer["loyalty_tier"] ?? "bronze").toString(),
      referralCode: (customer["referral_code"] ?? "").toString(),
      travelers: travelersRaw
          .map((item) => TravelerProfileModel.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  static int _toInt(dynamic value) {
    if (value is int) return value;
    return int.tryParse((value ?? "0").toString()) ?? 0;
  }
}
