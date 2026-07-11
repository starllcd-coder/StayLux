import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constants/app_constants.dart';

class SecureStorageService {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  Future<void> saveAccessToken(String token) async {
    await _storage.write(key: AppConstants.accessTokenKey, value: token);
  }

  Future<void> saveRefreshToken(String token) async {
    await _storage.write(key: AppConstants.refreshTokenKey, value: token);
  }

  Future<String?> getAccessToken() async {
    return _storage.read(key: AppConstants.accessTokenKey);
  }

  Future<String?> getRefreshToken() async {
    return _storage.read(key: AppConstants.refreshTokenKey);
  }

  Future<void> saveCustomerJson(Map<String, dynamic> json) async {
    await _storage.write(
      key: AppConstants.customerKey,
      value: jsonEncode(json),
    );
  }

  Future<Map<String, dynamic>?> getCustomerJson() async {
    final raw = await _storage.read(key: AppConstants.customerKey);
    if (raw == null || raw.isEmpty) return null;
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  Future<void> clearSession() async {
    await _storage.delete(key: AppConstants.accessTokenKey);
    await _storage.delete(key: AppConstants.refreshTokenKey);
    await _storage.delete(key: AppConstants.customerKey);
  }

  Future<void> saveString(String key, String value) async {
    await _storage.write(key: key, value: value);
  }

  Future<String?> getString(String key) async {
    return _storage.read(key: key);
  }

  Future<void> saveBool(String key, bool value) async {
    await _storage.write(key: key, value: value ? "1" : "0");
  }

  Future<bool> getBool(String key, {bool defaultValue = false}) async {
    final raw = await _storage.read(key: key);
    if (raw == null) return defaultValue;
    return raw == "1" || raw.toLowerCase() == "true";
  }
}
