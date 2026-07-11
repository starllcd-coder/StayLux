import '../../../../core/network/api_client.dart';
import '../models/user_model.dart';

class AuthApi {
  final ApiClient client;

  AuthApi(this.client);

  Future<({UserModel user, String accessToken, String refreshToken})> login(
    String email,
    String password,
  ) async {
    final response = await client.post(
      "/auth/login/",
      {
        "email": email,
        "password": password,
      },
    );

    final data = response.data as Map<String, dynamic>;
    final customer = data["customer"] as Map<String, dynamic>;
    final tokens = data["tokens"] as Map<String, dynamic>;

    return (
      user: UserModel.fromJson(customer),
      accessToken: (tokens["access"] ?? "").toString(),
      refreshToken: (tokens["refresh"] ?? "").toString(),
    );
  }

  Future<({UserModel user, String accessToken, String refreshToken})> register(
    String name,
    String email,
    String password, {
    String preferredCountry = "",
  }
  ) async {
    final response = await client.post(
      "/auth/register/",
      {
        "full_name": name,
        "email": email,
        "password": password,
        "confirm_password": password,
        "preferred_country": preferredCountry,
      },
    );

    final data = response.data as Map<String, dynamic>;
    final customer = data["customer"] as Map<String, dynamic>;
    final tokens = data["tokens"] as Map<String, dynamic>;

    return (
      user: UserModel.fromJson(customer),
      accessToken: (tokens["access"] ?? "").toString(),
      refreshToken: (tokens["refresh"] ?? "").toString(),
    );
  }

  Future<UserModel> getCurrentUser() async {
    final response = await client.get("/auth/me/");
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }
}
