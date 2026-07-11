import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/i18n/app_locale_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/repositories/token_storage.dart';
import '../../controllers/admin_auth_controller.dart';

class AdminLoginPage extends StatefulWidget {
  const AdminLoginPage({super.key});

  @override
  State<AdminLoginPage> createState() => _AdminLoginPageState();
}

class _AdminLoginPageState extends State<AdminLoginPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _authController = AdminAuthController();

  bool _rememberMe = true;
  bool _obscurePassword = true;
  bool _isLoading = false;
  String? _errorText;

  @override
  void initState() {
    super.initState();
    _rememberMe = TokenStorage.currentRememberMe;
    final rememberedLogin = TokenStorage.currentRememberedLogin;
    if (rememberedLogin != null && rememberedLogin.isNotEmpty) {
      _emailController.text = rememberedLogin;
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    FocusScope.of(context).unfocus();
    setState(() {
      _isLoading = true;
      _errorText = null;
    });

    try {
      await _authController.login(
        email: _emailController.text.trim(),
        password: _passwordController.text.trim(),
        rememberMe: _rememberMe,
      );

      if (!mounted) return;
      context.go('/admin/dashboard');
    } catch (e) {
      setState(() {
        _errorText = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  InputDecoration _fieldDecoration({
    required String hint,
    required IconData icon,
    Widget? suffix,
  }) {
    return InputDecoration(
      hintText: hint,
      prefixIcon: Icon(icon, color: const Color(0xFF7F8897), size: 20),
      suffixIcon: suffix,
      filled: true,
      fillColor: const Color(0xFFF4F5F8),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppTheme.luxuryGold, width: 1.4),
      ),
    );
  }

  Future<void> _openForgotPasswordHelp() async {
    final loginInput = _emailController.text.trim();
    Map<String, String> propertyContact = const {};
    if (loginInput.isNotEmpty) {
      try {
        propertyContact = await _authController.getRecoveryContact(
          loginInput: loginInput,
        );
      } catch (_) {
        propertyContact = const {};
      }
    }
    if (!mounted) return;

    final propertyName = propertyContact['propertyName'] ?? '';
    final propertyPhone = propertyContact['phone'] ?? '';
    final propertyWhatsApp = propertyContact['whatsapp'] ?? '';
    final propertyEmail = propertyContact['email'] ?? '';

    final showPropertyContact = propertyContact.isNotEmpty;
    await showDialog<void>(
      context: context,
      builder: (context) {
        final propertyContactText = [
          if (propertyName.isNotEmpty) '${context.tr('property_name')}: $propertyName',
          if (propertyPhone.isNotEmpty) '${context.tr('support_phone')}: $propertyPhone',
          if (propertyWhatsApp.isNotEmpty) '${context.tr('support_whatsapp')}: $propertyWhatsApp',
          if (propertyEmail.isNotEmpty) '${context.tr('support_email')}: $propertyEmail',
        ].join('\n');
        final fallbackContactText =
            '${context.tr('support_email')}: ${AppConfig.supportEmail}\n'
            '${context.tr('support_whatsapp')}: ${AppConfig.supportWhatsApp}';
        final copyText = showPropertyContact && propertyContactText.isNotEmpty
            ? propertyContactText
            : fallbackContactText;
        return AlertDialog(
          title: Text(context.tr('forgot_password_help_title')),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(context.tr('forgot_password_help_body')),
              const SizedBox(height: 10),
              if (showPropertyContact) ...[
                Text(
                  context.tr('property_contact_found'),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 6),
                if (propertyName.isNotEmpty)
                  Text('${context.tr('property_name')}: $propertyName'),
                if (propertyPhone.isNotEmpty)
                  Text('${context.tr('support_phone')}: $propertyPhone'),
                if (propertyWhatsApp.isNotEmpty)
                  Text('${context.tr('support_whatsapp')}: $propertyWhatsApp'),
                if (propertyEmail.isNotEmpty)
                  Text('${context.tr('support_email')}: $propertyEmail'),
              ] else ...[
                Text(context.tr('property_contact_not_found')),
                const SizedBox(height: 6),
                Text('${context.tr('support_email')}: ${AppConfig.supportEmail}'),
                Text('${context.tr('support_whatsapp')}: ${AppConfig.supportWhatsApp}'),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text(context.tr('close')),
            ),
            FilledButton(
              onPressed: () async {
                final navigator = Navigator.of(context);
                final messenger = ScaffoldMessenger.of(this.context);
                await Clipboard.setData(ClipboardData(text: copyText));
                if (!mounted) return;
                navigator.pop();
                messenger.showSnackBar(
                  SnackBar(content: Text(this.context.tr('contact_copied'))),
                );
              },
              child: Text(context.tr('contact_admin')),
            ),
            TextButton(
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(this.context);
                await Clipboard.setData(ClipboardData(text: copyText));
                if (!mounted) return;
                messenger.showSnackBar(
                  SnackBar(content: Text(this.context.tr('contact_copied'))),
                );
              },
              child: Text(context.tr('copy_contact')),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFFCFBF9), Color(0xFFF4F2EF)],
          ),
        ),
        child: Stack(
          children: [
            const _SoftGlow(top: -50, left: -40, size: 170),
            const _SoftGlow(bottom: -60, right: -40, size: 190),
            SafeArea(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 430),
                    child: Column(
                      children: [
                        Align(
                          alignment: Alignment.centerRight,
                          child: Material(
                            color: Colors.transparent,
                            child: Ink(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(999),
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFFF9EE), Color(0xFFF4E2B8)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                border: Border.all(
                                  color: const Color(0xFFE0C98E),
                                  width: 1.1,
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withValues(alpha: 0.08),
                                    blurRadius: 12,
                                    offset: const Offset(0, 4),
                                  ),
                                ],
                              ),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(999),
                                onTap: () async {
                                  await AppLocaleController.toggleLanguage();
                                },
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(
                                        Icons.language_outlined,
                                        size: 16,
                                        color: Color(0xFFA78646),
                                      ),
                                      const SizedBox(width: 6),
                                      Text(
                                        context.tr('language_switch'),
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w700,
                                          color: Color(0xFFA78646),
                                          letterSpacing: 0.2,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        Image.asset(
                          'assets/brand/AppIcon_1024x1024.png',
                          width: 220,
                          fit: BoxFit.contain,
                          filterQuality: FilterQuality.high,
                        ),
                        const SizedBox(height: 22),
                        Text(
                          context.tr('welcome'),
                          style: TextStyle(
                            fontSize: 52,
                            fontWeight: FontWeight.w800,
                            color: AppTheme.primaryNavy,
                            height: 1,
                          ),
                        ),
                        const SizedBox(height: 18),
                        Container(
                          padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(30),
                            border: Border.all(color: const Color(0xFFEFECE7)),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.07),
                                blurRadius: 22,
                                offset: const Offset(0, 10),
                              ),
                            ],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              TextField(
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                decoration: _fieldDecoration(
                                  hint: context.tr('email_address'),
                                  icon: Icons.mail_outline,
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextField(
                                controller: _passwordController,
                                obscureText: _obscurePassword,
                                decoration: _fieldDecoration(
                                  hint: context.tr('password'),
                                  icon: Icons.lock_outline,
                                  suffix: IconButton(
                                    onPressed: () {
                                      setState(() => _obscurePassword = !_obscurePassword);
                                    },
                                    icon: Icon(
                                      _obscurePassword
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                      color: const Color(0xFF7F8897),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 6),
                              Row(
                                children: [
                                  TextButton(
                                    onPressed: _openForgotPasswordHelp,
                                    child: Text(
                                      context.tr('forgot_password'),
                                      style: const TextStyle(
                                        color: Color(0xFF7F8897),
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                  const Spacer(),
                                  Checkbox(
                                    value: _rememberMe,
                                    activeColor: AppTheme.luxuryGold,
                                    onChanged: (value) {
                                      setState(() {
                                        _rememberMe = value ?? false;
                                      });
                                      TokenStorage.saveRememberMe(_rememberMe);
                                    },
                                  ),
                                  Text(
                                    context.tr('remember_me'),
                                    style: TextStyle(
                                      fontWeight: FontWeight.w600,
                                      color: Color(0xFF6F7786),
                                    ),
                                  ),
                                ],
                              ),
                              if (_errorText != null) ...[
                                const SizedBox(height: 6),
                                Text(
                                  _errorText!,
                                  style: const TextStyle(
                                    color: Colors.red,
                                    fontSize: 13,
                                  ),
                                ),
                              ],
                              const SizedBox(height: 6),
                              _isLoading
                                  ? const Center(child: CircularProgressIndicator())
                                  : SizedBox(
                                      width: double.infinity,
                                      child: ElevatedButton(
                                        onPressed: _login,
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: AppTheme.luxuryGold,
                                          foregroundColor: Colors.white,
                                          elevation: 0,
                                          padding: const EdgeInsets.symmetric(vertical: 16),
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(18),
                                          ),
                                        ),
                                        child: Text(
                                          context.tr('log_in'),
                                          style: TextStyle(
                                            fontSize: 18,
                                            fontWeight: FontWeight.w700,
                                            height: 1,
                                          ),
                                        ),
                                      ),
                                    ),
                            ],
                          ),
                        ),
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
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                const Color(0xFFD7B46B).withValues(alpha: 0.26),
                Colors.transparent,
              ],
            ),
          ),
        ),
      ),
    );
  }
}
