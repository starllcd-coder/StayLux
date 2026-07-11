import '../entities/profile.dart';

abstract class ProfileRepository {
  Future<CustomerProfile> getProfile();

  Future<CustomerProfile> updateProfile({
    required String fullName,
    required String email,
    required String mobile,
    required String preferredLanguage,
    required String preferredCountry,
  });

  Future<List<TravelerProfile>> getTravelers();

  Future<TravelerProfile> createTraveler({
    required String fullName,
    required String phone,
    required String whatsapp,
    required String email,
    required String nationality,
    required String idType,
    required String idNumber,
    required String idExpiry,
    required String address,
    required String notes,
    required bool isDefault,
  });

  Future<void> deleteTraveler(int travelerId);
}