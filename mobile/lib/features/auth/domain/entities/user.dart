class User {
  final int id;
  final String email;
  final String name;
  final String mobile;
  final String preferredLanguage;
  final String preferredCountry;
  final bool isVerified;
  final int loyaltyPoints;
  final String loyaltyTier;
  final String referralCode;

  User({
    required this.id,
    required this.email,
    required this.name,
    required this.mobile,
    required this.preferredLanguage,
    required this.preferredCountry,
    required this.isVerified,
    this.loyaltyPoints = 0,
    this.loyaltyTier = "bronze",
    this.referralCode = "",
  });
}
