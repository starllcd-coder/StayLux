import '../../../data/repositories/token_storage.dart';

class AdminSessionController {
  Future<bool> checkLoggedIn() async {
    return TokenStorage.isLoggedIn();
  }

  Future<void> clearSession() async {
    await TokenStorage.clear();
  }

  String? getCurrentRole() {
    return TokenStorage.currentRole;
  }

  String? getCurrentBackendRole() {
    return TokenStorage.currentBackendRole;
  }

  String? getCurrentUserName() {
    return TokenStorage.currentUserName;
  }

  String? getCurrentEmail() {
    return TokenStorage.currentEmail;
  }

  String? getCurrentUserId() {
    return TokenStorage.currentUserId;
  }

  List<String> getPropertyIds() {
    return TokenStorage.currentPropertyIds;
  }

  bool hasRole(String role) {
    return TokenStorage.hasRole(role);
  }

  bool hasAnyRole(List<String> roles) {
    return TokenStorage.hasAnyRole(roles);
  }

  bool canAccessProperty(String propertyId) {
    return TokenStorage.canAccessProperty(propertyId);
  }
}
