import 'package:flutter/material.dart';

import '../../data/repositories/token_storage.dart';
import 'app_i18n.dart';

class AppLocaleController {
  static final ValueNotifier<Locale> localeNotifier = ValueNotifier<Locale>(
    TokenStorage.currentLocaleCode == 'ar' ? AppI18n.arabic : AppI18n.english,
  );

  static bool get isArabic => localeNotifier.value.languageCode == 'ar';

  static Future<void> toggleLanguage() async {
    final locale = isArabic ? AppI18n.english : AppI18n.arabic;
    localeNotifier.value = locale;
    await TokenStorage.saveLocaleCode(locale.languageCode);
  }
}
