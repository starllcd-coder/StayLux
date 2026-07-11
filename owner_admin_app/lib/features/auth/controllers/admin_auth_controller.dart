import '../../../data/datasources/admin_api.dart';
import '../../../data/models/admin_user.dart';
import '../../../data/repositories/admin_repository.dart';
import '../../../data/repositories/token_storage.dart';

class AdminAuthController {
  final AdminRepository _repository = AdminRepository(AdminApi());

  Future<AdminUser> login({
    required String email,
    required String password,
    required bool rememberMe,
  }) async {
    final user = await _repository.login(email: email, password: password);

    await TokenStorage.saveSession(
      token: user.token,
      refreshToken: user.refreshToken,
      role: user.role,
      backendRole: user.backendRole,
      userName: user.name,
      email: user.email,
      userId: user.id,
      propertyIds: user.propertyIds,
      persist: rememberMe,
    );
    await TokenStorage.saveRememberMe(rememberMe);
    if (rememberMe) {
      await TokenStorage.saveRememberedIdentity(
        loginInput: email,
        userName: user.name,
        email: user.email,
      );
    } else {
      await TokenStorage.clearRememberedIdentity();
    }

    return user;
  }

  Future<Map<String, String>> getRecoveryContact({
    required String loginInput,
  }) async {
    final data = await _repository.getRecoveryContact(loginInput: loginInput);
    final found = data['found'] == true;
    if (!found) return const {};
    return {
      'propertyName': data['property_name']?.toString() ?? '',
      'phone': data['phone']?.toString() ?? '',
      'whatsapp': data['whatsapp']?.toString() ?? '',
      'email': data['email']?.toString() ?? '',
    };
  }

  Future<void> logout() async {
    await TokenStorage.clear();
  }

  Future<bool> isLoggedIn() async {
    return TokenStorage.isLoggedIn();
  }
}
