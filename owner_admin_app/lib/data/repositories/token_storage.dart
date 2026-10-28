import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorage {
  static Future<void> Function()? beforeClear;
  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  static const String _tokenKey = 'admin_token';
  static const String _refreshTokenKey = 'admin_refresh_token';
  static const String _roleKey = 'admin_role';
  static const String _backendRoleKey = 'admin_backend_role';
  static const String _userNameKey = 'admin_user_name';
  static const String _emailKey = 'admin_email';
  static const String _userIdKey = 'admin_user_id';
  static const String _propertyIdsKey = 'admin_property_ids';
  static const String _localeKey = 'app_locale';
  static const String _rememberMeKey = 'admin_remember_me';
  static const String _rememberedLoginKey = 'remembered_login';
  static const String _rememberedUserNameKey = 'remembered_user_name';
  static const String _rememberedEmailKey = 'remembered_email';

  static String? _cachedToken;
  static String? _cachedRefreshToken;
  static String? _cachedRole;
  static String? _cachedBackendRole;
  static String? _cachedUserName;
  static String? _cachedEmail;
  static String? _cachedUserId;
  static List<String> _cachedPropertyIds = [];
  static String? _cachedLocaleCode;
  static bool _cachedRememberMe = true;
  static String? _cachedRememberedLogin;
  static String? _cachedRememberedUserName;
  static String? _cachedRememberedEmail;

  static String? get currentToken => _cachedToken;
  static String? get currentRefreshToken => _cachedRefreshToken;
  static String? get currentRole => _cachedRole;
  static String? get currentBackendRole => _cachedBackendRole;
  static String? get currentUserName => _cachedUserName;
  static String? get currentEmail => _cachedEmail;
  static String? get currentUserId => _cachedUserId;
  static List<String> get currentPropertyIds => _cachedPropertyIds;
  static String? get currentLocaleCode => _cachedLocaleCode;
  static bool get currentRememberMe => _cachedRememberMe;
  static String? get currentRememberedLogin => _cachedRememberedLogin;
  static String? get currentRememberedUserName => _cachedRememberedUserName;
  static String? get currentRememberedEmail => _cachedRememberedEmail;

  static Future<void> init() async {
    _cachedToken = await _storage.read(key: _tokenKey);
    _cachedRefreshToken = await _storage.read(key: _refreshTokenKey);
    _cachedRole = await _storage.read(key: _roleKey);
    _cachedBackendRole = await _storage.read(key: _backendRoleKey);
    _cachedUserName = await _storage.read(key: _userNameKey);
    _cachedEmail = await _storage.read(key: _emailKey);
    _cachedUserId = await _storage.read(key: _userIdKey);
    _cachedLocaleCode = await _storage.read(key: _localeKey);
    final rememberMeRaw = await _storage.read(key: _rememberMeKey);
    _cachedRememberMe = rememberMeRaw == null ? true : rememberMeRaw == 'true';
    _cachedRememberedLogin = await _storage.read(key: _rememberedLoginKey);
    _cachedRememberedUserName = await _storage.read(key: _rememberedUserNameKey);
    _cachedRememberedEmail = await _storage.read(key: _rememberedEmailKey);

    final propertyIdsRaw = await _storage.read(key: _propertyIdsKey);
    _cachedPropertyIds = propertyIdsRaw == null || propertyIdsRaw.trim().isEmpty
        ? []
        : propertyIdsRaw.split(',');
  }

  static Future<void> saveSession({
    required String token,
    String? refreshToken,
    required String role,
    String? backendRole,
    required String userName,
    required String email,
    required String userId,
    required List<String> propertyIds,
    bool persist = true,
  }) async {
    _cachedToken = token;
    _cachedRefreshToken = refreshToken;
    _cachedRole = role;
    _cachedBackendRole = backendRole;
    _cachedUserName = userName;
    _cachedEmail = email;
    _cachedUserId = userId;
    _cachedPropertyIds = propertyIds;

    if (persist) {
      await _storage.write(key: _tokenKey, value: token);
      await _storage.write(key: _refreshTokenKey, value: refreshToken);
      await _storage.write(key: _roleKey, value: role);
      await _storage.write(key: _backendRoleKey, value: backendRole);
      await _storage.write(key: _userNameKey, value: userName);
      await _storage.write(key: _emailKey, value: email);
      await _storage.write(key: _userIdKey, value: userId);
      await _storage.write(key: _propertyIdsKey, value: propertyIds.join(','));
    } else {
      await _storage.delete(key: _tokenKey);
      await _storage.delete(key: _refreshTokenKey);
      await _storage.delete(key: _roleKey);
      await _storage.delete(key: _backendRoleKey);
      await _storage.delete(key: _userNameKey);
      await _storage.delete(key: _emailKey);
      await _storage.delete(key: _userIdKey);
      await _storage.delete(key: _propertyIdsKey);
    }
  }

  static Future<void> clear() async {
    try { await beforeClear?.call(); } catch (_) {}
    _cachedToken = null;
    _cachedRefreshToken = null;
    _cachedRole = null;
    _cachedBackendRole = null;
    _cachedUserName = null;
    _cachedEmail = null;
    _cachedUserId = null;
    _cachedPropertyIds = [];

    await _storage.delete(key: _tokenKey);
    await _storage.delete(key: _refreshTokenKey);
    await _storage.delete(key: _roleKey);
    await _storage.delete(key: _backendRoleKey);
    await _storage.delete(key: _userNameKey);
    await _storage.delete(key: _emailKey);
    await _storage.delete(key: _userIdKey);
    await _storage.delete(key: _propertyIdsKey);
  }

  static Future<void> saveLocaleCode(String localeCode) async {
    _cachedLocaleCode = localeCode;
    await _storage.write(key: _localeKey, value: localeCode);
  }

  static Future<void> saveRememberMe(bool rememberMe) async {
    _cachedRememberMe = rememberMe;
    await _storage.write(key: _rememberMeKey, value: rememberMe.toString());
  }

  static Future<void> saveRememberedIdentity({
    required String loginInput,
    required String userName,
    required String email,
  }) async {
    _cachedRememberedLogin = loginInput;
    _cachedRememberedUserName = userName;
    _cachedRememberedEmail = email;
    await _storage.write(key: _rememberedLoginKey, value: loginInput);
    await _storage.write(key: _rememberedUserNameKey, value: userName);
    await _storage.write(key: _rememberedEmailKey, value: email);
  }

  static Future<void> clearRememberedIdentity() async {
    _cachedRememberedLogin = null;
    _cachedRememberedUserName = null;
    _cachedRememberedEmail = null;
    await _storage.delete(key: _rememberedLoginKey);
    await _storage.delete(key: _rememberedUserNameKey);
    await _storage.delete(key: _rememberedEmailKey);
  }

  static Future<String?> getToken() async {
    if (_cachedToken != null) return _cachedToken;
    _cachedToken = await _storage.read(key: _tokenKey);
    return _cachedToken;
  }

  static Future<String?> getRefreshToken() async {
    if (_cachedRefreshToken != null) return _cachedRefreshToken;
    _cachedRefreshToken = await _storage.read(key: _refreshTokenKey);
    return _cachedRefreshToken;
  }

  static Future<void> saveTokens({
    required String token,
    required String refreshToken,
  }) async {
    _cachedToken = token;
    _cachedRefreshToken = refreshToken;
    await _storage.write(key: _tokenKey, value: token);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  static Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }

  static bool hasRole(String role) {
    return _cachedRole == role;
  }

  static bool hasAnyRole(List<String> roles) {
    return roles.contains(_cachedRole);
  }

  static bool canAccessProperty(String propertyId) {
    return _cachedPropertyIds.contains(propertyId);
  }
}
