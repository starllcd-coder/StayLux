class TravelerProfile {
  final int id;
  final String fullName;
  final String phone;
  final String whatsapp;
  final String email;
  final String nationality;
  final String idType;
  final String idNumber;
  final String idExpiry;
  final String address;
  final String notes;
  final bool isDefault;
  final bool isActive;

  TravelerProfile({
    required this.id,
    required this.fullName,
    required this.phone,
    required this.whatsapp,
    required this.email,
    required this.nationality,
    required this.idType,
    required this.idNumber,
    required this.idExpiry,
    required this.address,
    required this.notes,
    required this.isDefault,
    required this.isActive,
  });
}

class CustomerProfile {
  final int id;
  final String fullName;
  final String email;
  final String mobile;
  final String preferredLanguage;
  final String preferredCountry;
  final bool isVerified;
  final int loyaltyPoints;
  final String loyaltyTier;
  final String referralCode;
  final List<TravelerProfile> travelers;

  CustomerProfile({
    required this.id,
    required this.fullName,
    required this.email,
    required this.mobile,
    required this.preferredLanguage,
    required this.preferredCountry,
    required this.isVerified,
    this.loyaltyPoints = 0,
    this.loyaltyTier = "bronze",
    this.referralCode = "",
    required this.travelers,
  });
}
