import '../entities/user.dart';

abstract class AuthRepository {
  Future<({User user, String accessToken, String refreshToken})> login(
    String email,
    String password,
  );

  Future<({User user, String accessToken, String refreshToken})> register(
    String name,
    String email,
    String password, {
    String preferredCountry = "",
  }
  );

  Future<User> getCurrentUser();
}
