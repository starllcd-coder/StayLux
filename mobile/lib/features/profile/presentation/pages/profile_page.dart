import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/localization/app_locale_controller.dart';
import '../../../../core/localization/app_strings.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_button.dart';
import '../../../../core/widgets/app_empty_state.dart';
import '../../../../core/widgets/app_error_state.dart';
import '../../../../core/widgets/app_loader.dart';
import '../../../auth/presentation/controllers/auth_controller.dart';
import '../controllers/profile_controller.dart';

class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage> {
  final fullNameController = TextEditingController();
  final emailController = TextEditingController();
  final mobileController = TextEditingController();
  final preferredCountryController = TextEditingController();

  String preferredLanguage = "en";
  bool formInitialized = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(profileControllerProvider.notifier).load());
  }

  @override
  void dispose() {
    fullNameController.dispose();
    emailController.dispose();
    mobileController.dispose();
    preferredCountryController.dispose();
    super.dispose();
  }

  Future<void> _logout() async {
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text("Log out".tr(dialogContext)),
          content: Text("Are you sure you want to log out?".tr(dialogContext)),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: Text("Cancel".tr(dialogContext)),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: Text("Log out".tr(dialogContext)),
            ),
          ],
        );
      },
    );

    if (shouldLogout != true) return;
    await ref.read(authControllerProvider.notifier).logout();
    if (!mounted) return;
    context.go("/login");
  }

  void _fillForm(ProfileState state) {
    final profile = state.profile;
    if (profile == null) return;

    fullNameController.text = profile.fullName;
    emailController.text = profile.email;
    mobileController.text = profile.mobile;
    preferredCountryController.text = profile.preferredCountry;
    preferredLanguage =
        profile.preferredLanguage.isEmpty ? "en" : profile.preferredLanguage;
    formInitialized = true;
  }

  Future<void> _showAddTravelerDialog() async {
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    final whatsappController = TextEditingController();
    final emailController = TextEditingController();
    final nationalityController = TextEditingController();
    final idNumberController = TextEditingController();
    final idExpiryController = TextEditingController();
    final addressController = TextEditingController();
    final notesController = TextEditingController();

    String idType = "passport";
    bool isDefault = false;

    final formKey = GlobalKey<FormState>();

    Future<void> pickExpiry(StateSetter setModalState) async {
      final now = DateTime.now();
      final picked = await showDatePicker(
        context: context,
        firstDate: now,
        lastDate: DateTime(now.year + 15),
        initialDate: now,
      );

      if (picked != null) {
        idExpiryController.text =
            "${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}";
        setModalState(() {});
      }
    }

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.cardWhite,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.fromLTRB(
                16,
                16,
                16,
                MediaQuery.of(context).viewInsets.bottom + 16,
              ),
              child: SingleChildScrollView(
                child: Form(
                  key: formKey,
                  child: Column(
                    children: [
                      Text(
                        "Add Traveler".tr(context),
                        style: TextStyle(
                          color: AppTheme.darkText,
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: nameController,
                        decoration: InputDecoration(
                          labelText: "Full Name".tr(context),
                        ),
                        validator: (value) =>
                            value == null || value.trim().isEmpty
                                ? "Full name is required".tr(context)
                                : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: emailController,
                        decoration:
                            InputDecoration(labelText: "Email".tr(context)),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: phoneController,
                        decoration:
                            InputDecoration(labelText: "Phone".tr(context)),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: whatsappController,
                        decoration:
                            InputDecoration(labelText: "WhatsApp".tr(context)),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: nationalityController,
                        decoration: InputDecoration(
                          labelText: "Nationality".tr(context),
                        ),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        initialValue: idType,
                        decoration: InputDecoration(labelText: "ID Type".tr(context)),
                        items: [
                          DropdownMenuItem(
                            value: "passport",
                            child: Text("Passport".tr(context)),
                          ),
                          DropdownMenuItem(
                            value: "national_id",
                            child: Text("National ID".tr(context)),
                          ),
                          DropdownMenuItem(
                            value: "driving_license",
                            child: Text("Driving License".tr(context)),
                          ),
                        ],
                        onChanged: (value) {
                          setModalState(() {
                            idType = value ?? "passport";
                          });
                        },
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: idNumberController,
                        decoration:
                            InputDecoration(labelText: "ID Number".tr(context)),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: idExpiryController,
                        readOnly: true,
                        onTap: () => pickExpiry(setModalState),
                        decoration: InputDecoration(
                          labelText: "ID Expiry".tr(context),
                          prefixIcon: const Icon(Icons.calendar_month_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: addressController,
                        maxLines: 2,
                        decoration: InputDecoration(
                          labelText: "Address".tr(context),
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: notesController,
                        maxLines: 2,
                        decoration: InputDecoration(
                          labelText: "Notes".tr(context),
                          alignLabelWithHint: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      CheckboxListTile(
                        value: isDefault,
                        onChanged: (value) {
                          setModalState(() {
                            isDefault = value ?? false;
                          });
                        },
                        title: Text("Set as default traveler".tr(context)),
                        contentPadding: EdgeInsets.zero,
                        activeColor: AppTheme.luxuryGold,
                      ),
                      const SizedBox(height: 8),
                      AppButton(
                        text: "Save Traveler".tr(context),
                        onPressed: () async {
                          if (!formKey.currentState!.validate()) return;

                          final ok = await ref
                              .read(profileControllerProvider.notifier)
                              .createTraveler(
                                fullName: nameController.text.trim(),
                                phone: phoneController.text.trim(),
                                whatsapp: whatsappController.text.trim(),
                                email: emailController.text.trim(),
                                nationality: nationalityController.text.trim(),
                                idType: idType,
                                idNumber: idNumberController.text.trim(),
                                idExpiry: idExpiryController.text.trim(),
                                address: addressController.text.trim(),
                                notes: notesController.text.trim(),
                                isDefault: isDefault,
                              );

                          if (!mounted) return;

                          Navigator.of(this.context).pop();

                          ScaffoldMessenger.of(this.context).showSnackBar(
                            SnackBar(
                              content: Text(
                                ok
                                    ? "Traveler added".tr(this.context)
                                    : (ref
                                            .read(profileControllerProvider)
                                            .error ??
                                        "Failed to add traveler".tr(this.context)),
                              ),
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(profileControllerProvider);

    if (state.profile != null && !formInitialized) {
      _fillForm(state);
    }

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      appBar: AppBar(
        backgroundColor: AppTheme.ivory,
        title: Text(
          "Profile".tr(context),
          style: TextStyle(
            color: AppTheme.darkText,
            fontWeight: FontWeight.w700,
          ),
        ),
        actions: [
          IconButton(
            tooltip: "Log out".tr(context),
            onPressed: _logout,
            icon: const Icon(Icons.logout_rounded, color: AppTheme.primaryNavy),
          ),
        ],
      ),
      body: Builder(
        builder: (_) {
          if (state.isLoading) {
            return AppLoader(message: "Loading profile...".tr(context));
          }

          if (state.error != null && state.profile == null) {
            return AppErrorState(
              message: state.error,
              onRetry: () =>
                  ref.read(profileControllerProvider.notifier).load(),
            );
          }

          final profile = state.profile;
          if (profile == null) {
            return AppEmptyState(
              icon: Icons.person_off_outlined,
              title: "Profile not found",
              message: "We could not load your account details.",
              action: OutlinedButton(
                onPressed: () =>
                    ref.read(profileControllerProvider.notifier).load(),
                child: Text("Reload".tr(context)),
              ),
            );
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF132B52), Color(0xFF244A82)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "Loyalty".tr(context),
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        "${"Points".tr(context)}: ${profile.loyaltyPoints}",
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.95)),
                      ),
                      Text(
                        "${"Tier".tr(context)}: ${profile.loyaltyTier.toUpperCase()}",
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.95)),
                      ),
                      if (profile.referralCode.trim().isNotEmpty)
                        Text(
                          "${"Referral code".tr(context)}: ${profile.referralCode}",
                          style: TextStyle(color: Colors.white.withValues(alpha: 0.95)),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppTheme.cardWhite,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFE7DECC)),
                  ),
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      OutlinedButton.icon(
                        onPressed: () => context.push("/chat"),
                        icon: const Icon(Icons.chat_bubble_outline_rounded),
                        label: Text("Chat".tr(context)),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => context.push("/concierge"),
                        icon: const Icon(Icons.room_service_outlined),
                        label: Text("Concierge".tr(context)),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => context.push("/membership"),
                        icon: const Icon(Icons.workspace_premium_outlined),
                        label: Text("Membership".tr(context)),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => context.push("/security-center"),
                        icon: const Icon(Icons.verified_user_outlined),
                        label: Text("Security".tr(context)),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => context.push("/preferences"),
                        icon: const Icon(Icons.tune_outlined),
                        label: Text("Preferences".tr(context)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: AppTheme.cardWhite,
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: const Color(0xFFE7DECC)),
                  ),
                  child: Column(
                    children: [
                      const CircleAvatar(
                        radius: 34,
                        backgroundColor: Color(0xFFF2E9CF),
                        child: Icon(
                          Icons.person_outline_rounded,
                          color: AppTheme.primaryNavy,
                          size: 34,
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: fullNameController,
                        decoration: InputDecoration(
                          labelText: "Full Name".tr(context),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: emailController,
                        decoration: InputDecoration(labelText: "Email".tr(context)),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: mobileController,
                        decoration: InputDecoration(labelText: "Mobile".tr(context)),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        initialValue: preferredLanguage,
                        decoration: InputDecoration(
                          labelText: "Preferred Language".tr(context),
                        ),
                        items: [
                          DropdownMenuItem(
                            value: "en",
                            child: Text("English".tr(context)),
                          ),
                          DropdownMenuItem(
                            value: "ar",
                            child: Text("Arabic".tr(context)),
                          ),
                        ],
                        onChanged: (value) {
                          setState(() {
                            preferredLanguage = value ?? "en";
                          });
                          ref.read(appLocaleProvider.notifier).setLocale(
                                Locale(preferredLanguage == "ar" ? "ar" : "en"),
                              );
                        },
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: preferredCountryController,
                        decoration: InputDecoration(
                          labelText: "Preferred Country".tr(context),
                        ),
                      ),
                      const SizedBox(height: 18),
                      AppButton(
                        text: "Save Profile".tr(context),
                        isLoading: state.isSubmitting,
                        onPressed: () async {
                          final ok = await ref
                              .read(profileControllerProvider.notifier)
                              .update(
                                fullName: fullNameController.text.trim(),
                                email: emailController.text.trim(),
                                mobile: mobileController.text.trim(),
                                preferredLanguage: preferredLanguage,
                                preferredCountry:
                                    preferredCountryController.text.trim(),
                              );

                          if (!mounted) return;

                          ScaffoldMessenger.of(this.context).showSnackBar(
                            SnackBar(
                              content: Text(
                                ok
                                    ? "Profile updated".tr(this.context)
                                    : (ref
                                            .read(profileControllerProvider)
                                            .error ??
                                        "Update failed".tr(this.context)),
                              ),
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: AppTheme.cardWhite,
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: const Color(0xFFE7DECC)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            "Traveler Profiles".tr(context),
                            style: TextStyle(
                              color: AppTheme.darkText,
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const Spacer(),
                          TextButton.icon(
                            onPressed: _showAddTravelerDialog,
                            icon: const Icon(Icons.add_rounded),
                            label: Text("Add".tr(context)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      if (profile.travelers.isEmpty)
                        AppEmptyState(
                          icon: Icons.badge_outlined,
                          title: "No traveler profiles",
                          message:
                              "Add traveler details to make future bookings faster.",
                          action: AppButton(
                            text: "Add Traveler".tr(context),
                            onPressed: _showAddTravelerDialog,
                          ),
                        )
                      else
                        ...profile.travelers.map(
                          (traveler) => Container(
                            margin: const EdgeInsets.only(bottom: 12),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: const Color(0xFFFAF8F2),
                              borderRadius: BorderRadius.circular(14),
                              border:
                                  Border.all(color: const Color(0xFFE5DECF)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  traveler.fullName,
                                  style: const TextStyle(
                                    color: AppTheme.darkText,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  "${traveler.idType} - ${traveler.idNumber}",
                                  style: const TextStyle(
                                      color: AppTheme.mutedText),
                                ),
                                const SizedBox(height: 10),
                                if (traveler.isDefault)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 5),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFF2E9CF),
                                      borderRadius: BorderRadius.circular(20),
                                    ),
                                    child: Text(
                                      "Default".tr(context),
                                      style: TextStyle(
                                        color: AppTheme.primaryNavy,
                                        fontWeight: FontWeight.w700,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                const SizedBox(height: 10),
                                Align(
                                  alignment: Alignment.centerRight,
                                  child: TextButton(
                                    onPressed: () async {
                                      final ok = await ref
                                          .read(profileControllerProvider
                                              .notifier)
                                          .deleteTraveler(traveler.id);

                                      if (!mounted) return;

                                      ScaffoldMessenger.of(this.context)
                                          .showSnackBar(
                                        SnackBar(
                                          content: Text(
                                            ok
                                                ? "Traveler removed".tr(this.context)
                                                : (ref
                                                        .read(
                                                            profileControllerProvider)
                                                        .error ??
                                                    "Failed"),
                                          ),
                                        ),
                                      );
                                    },
                                    child: Text("Remove".tr(context)),
                                  ),
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
        },
      ),
    );
  }
}

