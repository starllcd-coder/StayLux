class AppConstants {
  static const String apiBaseUrl = String.fromEnvironment(
    "STAYLUX_API_BASE_URL",
    defaultValue: "http://127.0.0.1:8000/api/mobile",
  );

  static const String accessTokenKey = "staylux_access_token";
  static const String refreshTokenKey = "staylux_refresh_token";
  static const String customerKey = "staylux_customer_json";
  static const String cacheDiscoveryKey = "staylux_cache_discovery";
  static const String cacheWishlistKey = "staylux_cache_wishlist";
  static const String cacheNotificationsKey = "staylux_cache_notifications";
  static const String pushDeviceTokenKey = "staylux_push_device_token";
  static const String wishlistOpsQueueKey = "staylux_wishlist_ops_queue";
  static const String rememberedEmailKey = "staylux_remembered_email";
  static const String rememberedPasswordKey = "staylux_remembered_password";
  static const String biometricEnabledKey = "staylux_biometric_enabled";
  static const String selectedCountryKey = "staylux_selected_country";
  static const String selectedCityKey = "staylux_selected_city";
  static const String selectedLanguageCodeKey = "staylux_selected_language_code";
}
