import 'package:flutter/material.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../data/datasources/profile_services_api.dart';

class SecurityCenterPage extends StatefulWidget {
  const SecurityCenterPage({super.key});

  @override
  State<SecurityCenterPage> createState() => _SecurityCenterPageState();
}

class _SecurityCenterPageState extends State<SecurityCenterPage> {
  final api = ProfileServicesApi(ApiClient());
  final emailCodeController = TextEditingController();
  final twoFaCodeController = TextEditingController();

  String emailDevCode = "";
  String twoFaDevCode = "";
  bool busy = false;
  String? error;

  @override
  void dispose() {
    emailCodeController.dispose();
    twoFaCodeController.dispose();
    super.dispose();
  }

  Future<void> _requestCode(String purpose) async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final payload = await api.requestVerification(purpose: purpose);
      setState(() {
        busy = false;
        if (purpose == "email_verify") {
          emailDevCode = (payload["dev_code"] ?? "").toString();
        } else {
          twoFaDevCode = (payload["dev_code"] ?? "").toString();
        }
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            (payload["message"] ?? "Code sent".tr(context)).toString(),
          ),
        ),
      );
    } catch (e) {
      setState(() {
        busy = false;
        error = e.toString();
      });
    }
  }

  Future<void> _verify(String purpose, String code) async {
    if (code.trim().isEmpty) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final payload = await api.verifyCode(purpose: purpose, code: code.trim());
      setState(() => busy = false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            (payload["message"] ?? "Verification successful".tr(context))
                .toString(),
          ),
        ),
      );
    } catch (e) {
      setState(() {
        busy = false;
        error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.ivory,
      appBar: AppBar(
        backgroundColor: AppTheme.ivory,
        title: Text(
          "Security Center".tr(context),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (error != null) Text(error!, style: const TextStyle(color: Colors.red)),
            _SecurityCard(
              title: "Email Verification".tr(context),
              subtitle:
                  "Verify your email to secure account recovery.".tr(context),
              onRequest: busy ? null : () => _requestCode("email_verify"),
              field: TextField(
                controller: emailCodeController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  hintText: "Enter 6-digit code".tr(context),
                ),
              ),
              onVerify: busy ? null : () => _verify("email_verify", emailCodeController.text),
              devCode: emailDevCode,
            ),
            const SizedBox(height: 12),
            _SecurityCard(
              title: "Two-Factor Authentication".tr(context),
              subtitle: "Enable a second step during login.".tr(context),
              onRequest: busy ? null : () => _requestCode("two_factor"),
              field: TextField(
                controller: twoFaCodeController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  hintText: "Enter 6-digit code".tr(context),
                ),
              ),
              onVerify: busy ? null : () => _verify("two_factor", twoFaCodeController.text),
              devCode: twoFaDevCode,
            ),
          ],
        ),
      ),
    );
  }
}

class _SecurityCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final VoidCallback? onRequest;
  final Widget field;
  final VoidCallback? onVerify;
  final String devCode;

  const _SecurityCard({
    required this.title,
    required this.subtitle,
    required this.onRequest,
    required this.field,
    required this.onVerify,
    required this.devCode,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(color: AppTheme.mutedText)),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton(
                onPressed: onRequest,
                style: FilledButton.styleFrom(backgroundColor: AppTheme.primaryNavy),
                child: Text("Request Code".tr(context)),
              ),
              if (devCode.trim().isNotEmpty)
                Text(
                  "${"Dev code".tr(context)}: $devCode",
                  style: const TextStyle(color: AppTheme.mutedText),
                ),
            ],
          ),
          const SizedBox(height: 10),
          field,
          const SizedBox(height: 10),
          FilledButton(
            onPressed: onVerify,
            style: FilledButton.styleFrom(backgroundColor: AppTheme.luxuryGold),
            child: Text("Verify".tr(context)),
          ),
        ],
      ),
    );
  }
}
