import 'package:flutter/material.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../data/datasources/profile_services_api.dart';

class AccountPreferencesPage extends StatefulWidget {
  const AccountPreferencesPage({super.key});

  @override
  State<AccountPreferencesPage> createState() => _AccountPreferencesPageState();
}

class _AccountPreferencesPageState extends State<AccountPreferencesPage> {
  final api = ProfileServicesApi(ApiClient());
  final brandController = TextEditingController();
  final last4Controller = TextEditingController();
  final expMonthController = TextEditingController();
  final expYearController = TextEditingController();

  bool busy = false;
  String? error;
  List<Map<String, dynamic>> paymentMethods = const [];
  bool marketingOptIn = false;
  bool emailEnabled = true;
  bool pushEnabled = true;
  bool smsEnabled = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(_load);
  }

  @override
  void dispose() {
    brandController.dispose();
    last4Controller.dispose();
    expMonthController.dispose();
    expYearController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final methods = await api.getPaymentMethods();
      final settings = await api.getNotificationSettings();
      setState(() {
        paymentMethods = methods;
        marketingOptIn = settings["marketing_opt_in"] == true;
        emailEnabled = settings["email_notifications_enabled"] != false;
        pushEnabled = settings["push_notifications_enabled"] != false;
        smsEnabled = settings["sms_notifications_enabled"] == true;
        busy = false;
      });
    } catch (e) {
      setState(() {
        error = e.toString();
        busy = false;
      });
    }
  }

  Future<void> _saveSettings() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await api.updateNotificationSettings(
        marketingOptIn: marketingOptIn,
        emailEnabled: emailEnabled,
        pushEnabled: pushEnabled,
        smsEnabled: smsEnabled,
      );
      setState(() => busy = false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Notification settings updated".tr(context))),
      );
    } catch (e) {
      setState(() {
        busy = false;
        error = e.toString();
      });
    }
  }

  Future<void> _addPaymentMethod() async {
    final brand = brandController.text.trim();
    final last4 = last4Controller.text.trim();
    final expMonth = int.tryParse(expMonthController.text.trim()) ?? 0;
    final expYear = int.tryParse(expYearController.text.trim()) ?? 0;
    if (brand.isEmpty || last4.length != 4 || expMonth < 1 || expMonth > 12 || expYear < 2024) {
      setState(() => error = "Enter a valid payment method.".tr(context));
      return;
    }

    setState(() {
      busy = true;
      error = null;
    });
    try {
      await api.addPaymentMethod(
        brand: brand,
        last4: last4,
        expMonth: expMonth,
        expYear: expYear,
        isDefault: paymentMethods.isEmpty,
      );
      brandController.clear();
      last4Controller.clear();
      expMonthController.clear();
      expYearController.clear();
      await _load();
    } catch (e) {
      setState(() {
        busy = false;
        error = e.toString();
      });
    }
  }

  Future<void> _setDefault(int id) async {
    setState(() => busy = true);
    try {
      await api.setDefaultPaymentMethod(id);
      await _load();
    } catch (e) {
      setState(() {
        busy = false;
        error = e.toString();
      });
    }
  }

  Future<void> _remove(int id) async {
    setState(() => busy = true);
    try {
      await api.removePaymentMethod(id);
      await _load();
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
          "Preferences".tr(context),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(error!, style: const TextStyle(color: Colors.red)),
            ),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Notification Settings".tr(context),
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                ),
                SwitchListTile(
                  value: pushEnabled,
                  onChanged: busy ? null : (v) => setState(() => pushEnabled = v),
                  title: Text("Push notifications".tr(context)),
                  contentPadding: EdgeInsets.zero,
                ),
                SwitchListTile(
                  value: emailEnabled,
                  onChanged: busy ? null : (v) => setState(() => emailEnabled = v),
                  title: Text("Email notifications".tr(context)),
                  contentPadding: EdgeInsets.zero,
                ),
                SwitchListTile(
                  value: smsEnabled,
                  onChanged: busy ? null : (v) => setState(() => smsEnabled = v),
                  title: Text("SMS notifications".tr(context)),
                  contentPadding: EdgeInsets.zero,
                ),
                SwitchListTile(
                  value: marketingOptIn,
                  onChanged: busy ? null : (v) => setState(() => marketingOptIn = v),
                  title: Text("Marketing offers".tr(context)),
                  contentPadding: EdgeInsets.zero,
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton(
                    onPressed: busy ? null : _saveSettings,
                    style: FilledButton.styleFrom(backgroundColor: AppTheme.primaryNavy),
                    child: Text("Save".tr(context)),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Payment Methods".tr(context),
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: brandController,
                  decoration: InputDecoration(labelText: "Card brand".tr(context)),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: last4Controller,
                  keyboardType: TextInputType.number,
                  maxLength: 4,
                  decoration: InputDecoration(labelText: "Last 4 digits".tr(context)),
                ),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: expMonthController,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(labelText: "Exp month".tr(context)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: expYearController,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(labelText: "Exp year".tr(context)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton(
                    onPressed: busy ? null : _addPaymentMethod,
                    style: FilledButton.styleFrom(backgroundColor: AppTheme.luxuryGold),
                    child: Text("Add Card".tr(context)),
                  ),
                ),
                const SizedBox(height: 8),
                if (paymentMethods.isEmpty)
                  Text("No saved payment methods.".tr(context))
                else
                  ...paymentMethods.map(
                    (item) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.credit_card_outlined),
                      title: Text(
                        "${item["brand"] ?? "Card".tr(context)} ${item["masked_number"] ?? ""}",
                      ),
                      subtitle: Text(
                        "${"Exp".tr(context)} ${item["exp_month"]}/${item["exp_year"]}",
                      ),
                      trailing: Wrap(
                        spacing: 4,
                        children: [
                          if (item["is_default"] == true)
                            Chip(label: Text("Default".tr(context)))
                          else
                            TextButton(
                              onPressed: busy
                                  ? null
                                  : () => _setDefault(int.tryParse((item["id"] ?? "0").toString()) ?? 0),
                              child: Text("Set default".tr(context)),
                            ),
                          IconButton(
                            onPressed: busy
                                ? null
                                : () => _remove(int.tryParse((item["id"] ?? "0").toString()) ?? 0),
                            icon: const Icon(Icons.delete_outline),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
