import 'package:flutter/material.dart';

import '../../../../core/widgets/language_toggle_button.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/localization/app_strings.dart';
import '../widgets/login_form.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFFCFBF9), Color(0xFFF4F2EF)],
          ),
        ),
        child: Stack(
          children: [
            const _SoftGlow(top: -60, left: -45, size: 190),
            const _SoftGlow(bottom: -80, right: -50, size: 220),
            SafeArea(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 430),
                    child: Column(
                      children: [
                        const Align(
                          alignment: Alignment.centerRight,
                          child: LanguageToggleButton(),
                        ),
                        SizedBox(height: 10),
                        _BrandHeader(),
                        SizedBox(height: 16),
                        LoginForm(),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BrandHeader extends StatelessWidget {
  const _BrandHeader();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Image.asset(
          'assets/brand/StayLux1.png',
          width: 260,
          fit: BoxFit.contain,
          filterQuality: FilterQuality.high,
        ),
        const SizedBox(height: 20),
        Text(
          "Welcome".tr(context),
          style: TextStyle(
            fontSize: 52,
            fontWeight: FontWeight.w800,
            color: AppTheme.primaryNavy,
            height: 1,
          ),
        ),
      ],
    );
  }
}

class _SoftGlow extends StatelessWidget {
  final double? top;
  final double? left;
  final double? right;
  final double? bottom;
  final double size;

  const _SoftGlow({
    this.top,
    this.left,
    this.right,
    this.bottom,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: top,
      left: left,
      right: right,
      bottom: bottom,
      child: IgnorePointer(
        child: Container(
          width: size,
          height: size,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [Color(0x3DD7B46B), Colors.transparent],
            ),
          ),
        ),
      ),
    );
  }
}
