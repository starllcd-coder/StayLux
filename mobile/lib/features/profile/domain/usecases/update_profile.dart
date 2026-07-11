import '../entities/profile.dart';
import '../repositories/profile_repository.dart';

class UpdateProfile {
  final ProfileRepository repository;

  UpdateProfile(this.repository);

  Future<CustomerProfile> call({
    required String fullName,
    required String email,
    required String mobile,
    required String preferredLanguage,
    required String preferredCountry,
  }) {
    return repository.updateProfile(
      fullName: fullName,
      email: email,
      mobile: mobile,
      preferredLanguage: preferredLanguage,
      preferredCountry: preferredCountry,
    );
  }
}