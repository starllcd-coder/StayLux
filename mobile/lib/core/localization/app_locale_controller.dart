import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../constants/app_constants.dart';
import '../storage/secure_storage_service.dart';

final appLocaleProvider =
    StateNotifierProvider<AppLocaleController, Locale>((ref) {
  return AppLocaleController();
});

class AppLocaleController extends StateNotifier<Locale> {
  AppLocaleController() : super(const Locale("en"));

  final _storage = SecureStorageService();

  bool get isArabic => state.languageCode == "ar";

  Future<void> bootstrap() async {
    final savedCode =
        (await _storage.getString(AppConstants.selectedLanguageCodeKey) ?? "en")
            .trim()
            .toLowerCase();
    state = Locale(savedCode == "ar" ? "ar" : "en");
  }

  Future<void> setLocale(Locale locale) async {
    final code = locale.languageCode.toLowerCase() == "ar" ? "ar" : "en";
    await _storage.saveString(AppConstants.selectedLanguageCodeKey, code);
    state = Locale(code);
  }

  Future<void> toggle() async {
    await setLocale(isArabic ? const Locale("en") : const Locale("ar"));
  }
}
