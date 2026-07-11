import 'package:flutter/material.dart';

class AppTheme {
  static const Color primaryNavy = Color(0xFF0E2A47);
  static const Color luxuryGold = Color(0xFFC8A96A);
  static const Color lightBg = Color(0xFFF6F3EC);

  static ThemeData get theme {
    return ThemeData(
      scaffoldBackgroundColor: lightBg,
      fontFamily: 'Poppins',
      useMaterial3: true,
    );
  }

  static ThemeData themeForLocale(Locale locale) {
    final isArabic = locale.languageCode == 'ar';
    return ThemeData(
      scaffoldBackgroundColor: lightBg,
      fontFamily: isArabic ? 'Cairo' : 'Poppins',
      useMaterial3: true,
    );
  }
}
