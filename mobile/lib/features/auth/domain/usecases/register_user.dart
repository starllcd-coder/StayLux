import '../entities/user.dart';
import '../repositories/auth_repository.dart';

class RegisterUser {
  final AuthRepository repository;

  RegisterUser(this.repository);

  Future<({User user, String accessToken, String refreshToken})> call(
    String name,
    String email,
    String password, {
    String preferredCountry = "",
  }
  ) {
    return repository.register(
      name,
      email,
      password,
      preferredCountry: preferredCountry,
    );
  }
}
