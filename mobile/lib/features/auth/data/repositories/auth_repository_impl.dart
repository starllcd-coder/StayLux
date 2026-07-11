import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_api.dart';

class AuthRepositoryImpl implements AuthRepository {
  final AuthApi api;

  AuthRepositoryImpl(this.api);

  @override
  Future<({User user, String accessToken, String refreshToken})> login(
    String email,
    String password,
  ) {
    return api.login(email, password);
  }

  @override
  Future<({User user, String accessToken, String refreshToken})> register(
    String name,
    String email,
    String password, {
    String preferredCountry = "",
  }
  ) {
    return api.register(
      name,
      email,
      password,
      preferredCountry: preferredCountry,
    );
  }

  @override
  Future<User> getCurrentUser() {
    return api.getCurrentUser();
  }
}
