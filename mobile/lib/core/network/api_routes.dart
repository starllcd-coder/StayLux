import '../constants/app_constants.dart';

class ApiRoutes {
  static const baseUrl = AppConstants.apiBaseUrl;

  static const login = "$baseUrl/auth/login/";
  static const register = "$baseUrl/auth/register/";
  static const profile = "$baseUrl/auth/me/";
}
