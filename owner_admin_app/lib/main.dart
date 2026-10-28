import 'core/services/staff_job_banner.dart';
import 'core/services/firebase_push_service.dart';
import 'package:flutter/material.dart';
import 'dart:ui';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'core/i18n/app_i18n.dart';
import 'core/i18n/app_locale_controller.dart';
import 'core/router/app_router.dart';
import 'core/services/telemetry_service.dart';
import 'core/theme/app_theme.dart';
import 'data/repositories/token_storage.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  TelemetryService.instance.initialize();
  FlutterError.onError = (details) {
    TelemetryService.instance.reportError(
      details.exception,
      details.stack ?? StackTrace.current,
      source: 'flutter_error',
      fatal: true,
    );
    FlutterError.presentError(details);
  };
  PlatformDispatcher.instance.onError = (error, stack) {
    TelemetryService.instance.reportError(
      error,
      stack,
      source: 'platform_dispatcher',
      fatal: true,
    );
    return false;
  };
  await TokenStorage.init();
  await FirebasePushService.instance.initialize();
  TokenStorage.beforeClear = FirebasePushService.instance.unregister;
  FirebasePushService.instance.onOpenInbox = () => appRouter.go('/admin/job-notifications');
  runApp(const StayLuxAdminApp());
}

class StayLuxAdminApp extends StatelessWidget {
  const StayLuxAdminApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<Locale>(
      valueListenable: AppLocaleController.localeNotifier,
      builder: (context, locale, _) {
        return MaterialApp.router(
          debugShowCheckedModeBanner: false,
          routerConfig: appRouter,
          builder: (context, child) => StaffJobBanner(
            onOpen: () => appRouter.go('/admin/job-notifications'),
            child: child ?? const SizedBox.shrink(),
          ),
          title: 'StayLux Admin',
          theme: AppTheme.themeForLocale(locale),
          locale: locale,
          supportedLocales: const [AppI18n.english, AppI18n.arabic],
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
          ],
        );
      },
    );
  }
}
