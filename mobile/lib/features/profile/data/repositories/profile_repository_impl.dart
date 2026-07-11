import '../../domain/entities/profile.dart';
import '../../domain/repositories/profile_repository.dart';
import '../datasources/profile_api.dart';

class ProfileRepositoryImpl implements ProfileRepository {
  final ProfileApi api;

  ProfileRepositoryImpl(this.api);

  @override
  Future<CustomerProfile> getProfile() {
    return api.getProfile();
  }

  @override
  Future<CustomerProfile> updateProfile({
    required String fullName,
    required String email,
    required String mobile,
    required String preferredLanguage,
    required String preferredCountry,
  }) {
    return api.updateProfile(
      fullName: fullName,
      email: email,
      mobile: mobile,
      preferredLanguage: preferredLanguage,
      preferredCountry: preferredCountry,
    );
  }

  @override
  Future<List<TravelerProfile>> getTravelers() {
    return api.getTravelers();
  }

  @override
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
  }) {
    return api.createTraveler(
      fullName: fullName,
      phone: phone,
      whatsapp: whatsapp,
      email: email,
      nationality: nationality,
      idType: idType,
      idNumber: idNumber,
      idExpiry: idExpiry,
      address: address,
      notes: notes,
      isDefault: isDefault,
    );
  }

  @override
  Future<void> deleteTraveler(int travelerId) {
    return api.deleteTraveler(travelerId);
  }
}