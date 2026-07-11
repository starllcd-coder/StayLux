import 'package:flutter/material.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../data/datasources/profile_services_api.dart';

class MembershipPage extends StatefulWidget {
  const MembershipPage({super.key});

  @override
  State<MembershipPage> createState() => _MembershipPageState();
}

class _MembershipPageState extends State<MembershipPage> {
  final api = ProfileServicesApi(ApiClient());
  final referralEmailController = TextEditingController();
  bool loading = true;
  List<Map<String, dynamic>> plans = const [];
  List<Map<String, dynamic>> memberships = const [];
  List<Map<String, dynamic>> referrals = const [];
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    referralEmailController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final p = await api.getMembershipPlans();
      final m = await api.getMemberships();
      final r = await api.getReferrals();
      setState(() {
        plans = p;
        memberships = m;
        referrals = r;
        loading = false;
      });
    } catch (e) {
      setState(() {
        loading = false;
        error = e.toString();
      });
    }
  }

  Future<void> _subscribe(int planId) async {
    try {
      await api.subscribePlan(planId);
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Membership activated".tr(context))),
      );
    } catch (e) {
      setState(() => error = e.toString());
    }
  }

  Future<void> _invite() async {
    final email = referralEmailController.text.trim();
    if (email.isEmpty) return;
    try {
      await api.createReferral(email);
      referralEmailController.clear();
      final r = await api.getReferrals();
      setState(() => referrals = r);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Referral invite sent".tr(context))),
      );
    } catch (e) {
      setState(() => error = e.toString());
    }
  }

  int _toInt(dynamic v) => int.tryParse(v?.toString() ?? "") ?? 0;

  @override
  Widget build(BuildContext context) {
    final active = memberships.where((m) => (m["status"] ?? "") == "active").toList();

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      appBar: AppBar(
        backgroundColor: AppTheme.ivory,
        title: Text(
          "Membership & Referral".tr(context),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (error != null) Text(error!, style: const TextStyle(color: Colors.red)),
                  if (active.isNotEmpty)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFFAEE),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        "${"Active plan".tr(context)}: ${(active.first["plan_name"] ?? "").toString()}",
                      ),
                    ),
                  const SizedBox(height: 12),
                  Text(
                    "Plans".tr(context),
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...plans.map(
                    (plan) {
                      final planId = _toInt(plan["id"]);
                      final benefits = (plan["benefits"] is List) ? plan["benefits"] as List : const [];
                      return Card(
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                (plan["name"] ?? "").toString(),
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                "${"Monthly".tr(context)} ${(plan["monthly_fee"] ?? "0").toString()} | ${"Annual".tr(context)} ${(plan["annual_fee"] ?? "0").toString()}",
                              ),
                              const SizedBox(height: 8),
                              ...benefits.map((b) => Text("- ${b.toString()}")),
                              const SizedBox(height: 8),
                              FilledButton(
                                onPressed: () => _subscribe(planId),
                                style: FilledButton.styleFrom(backgroundColor: AppTheme.luxuryGold),
                                child: Text("Subscribe".tr(context)),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 16),
                  Text(
                    "Referral Program".tr(context),
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: referralEmailController,
                          keyboardType: TextInputType.emailAddress,
                          decoration: InputDecoration(
                            hintText: "friend@email.com",
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      FilledButton(
                        onPressed: _invite,
                        style: FilledButton.styleFrom(backgroundColor: AppTheme.primaryNavy),
                        child: Text("Invite".tr(context)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  if (referrals.isEmpty)
                    Text("No referral invites yet.".tr(context))
                  else
                    ...referrals.map(
                      (r) => ListTile(
                        dense: true,
                        title: Text((r["referred_email"] ?? "").toString()),
                        subtitle: Text((r["status"] ?? "").toString()),
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}
