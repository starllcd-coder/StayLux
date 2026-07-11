import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/region/app_region_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/utils/gcc_region.dart';
import '../../../../core/widgets/app_button.dart';
import '../../../../core/widgets/language_toggle_button.dart';

class CountrySelectionPage extends ConsumerStatefulWidget {
  const CountrySelectionPage({super.key});

  @override
  ConsumerState<CountrySelectionPage> createState() =>
      _CountrySelectionPageState();
}

class _CountrySelectionPageState extends ConsumerState<CountrySelectionPage> {
  String selectedCountry = "";
  String selectedCity = "";

  static const _countryCities = <String, int>{
    "Oman": 4,
    "Qatar": 3,
    "United Arab Emirates": 4,
    "Saudi Arabia": 6,
    "Kuwait": 2,
    "Bahrain": 2,
  };

  static const _countryCodes = <String, String>{
    "Oman": "OM",
    "Qatar": "QA",
    "United Arab Emirates": "AE",
    "Saudi Arabia": "SA",
    "Kuwait": "KW",
    "Bahrain": "BH",
  };

  static const _countryCitiesList = <String, List<String>>{
    "Oman": <String>["Muscat", "Salalah", "Sohar", "Nizwa"],
    "Qatar": <String>["Doha", "Al Wakrah", "Al Khor"],
    "United Arab Emirates": <String>["Dubai", "Abu Dhabi", "Sharjah", "Ajman"],
    "Saudi Arabia": <String>["Riyadh", "Jeddah", "Dammam", "Makkah", "Madinah", "Al Khobar"],
    "Kuwait": <String>["Kuwait City", "Hawally"],
    "Bahrain": <String>["Manama", "Muharraq"],
  };

  @override
  void initState() {
    super.initState();
    final current = ref.read(appRegionProvider).country.trim();
    final currentCity = ref.read(appRegionProvider).city.trim();
    if (current.isNotEmpty) {
      selectedCountry = current;
    }
    if (currentCity.isNotEmpty) {
      selectedCity = currentCity;
    }
  }

  @override
  Widget build(BuildContext context) {
    final appRegion = ref.watch(appRegionProvider);
    final active = selectedCountry.isEmpty ? appRegion.country : selectedCountry;
    final isArabic = Directionality.of(context) == TextDirection.rtl;

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "Welcome to StayLux".tr(context),
                style: TextStyle(
                  color: AppTheme.darkText,
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                "Choose your country to localize pricing and discovery."
                    .tr(context),
                style: const TextStyle(color: AppTheme.mutedText, fontSize: 14),
              ),
              const SizedBox(height: 24),
              Align(
                alignment:
                    isArabic ? Alignment.centerRight : Alignment.centerLeft,
                child: const LanguageToggleButton(),
              ),
              const SizedBox(height: 14),
              Expanded(
                child: ListView.separated(
                  itemCount: gccCountries.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final country = gccCountries[index];
                    final selected =
                        active.toLowerCase() == country.toLowerCase();
                    final currency = currencyForCountry(country);
                    final cities = _countryCities[country] ?? 0;
                    final code = _countryCodes[country] ?? "--";

                    return InkWell(
                      borderRadius: BorderRadius.circular(16),
                      onTap: () => setState(() {
                        if (selectedCountry != country) {
                          selectedCity = "";
                        }
                        selectedCountry = country;
                      }),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 14,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: selected
                                ? const Color(0xFF2453A4)
                                : const Color(0xFFE2E5EC),
                            width: selected ? 1.5 : 1,
                          ),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 36,
                              height: 24,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(6),
                                color: const Color(0xFFF4F6FA),
                                border: Border.all(
                                  color: const Color(0xFFD7DDEA),
                                ),
                              ),
                              child: Text(
                                code,
                                style: const TextStyle(
                                  color: AppTheme.primaryNavy,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    country.tr(context),
                                    style: const TextStyle(
                                      color: AppTheme.primaryNavy,
                                      fontSize: 16,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    "${"Currency".tr(context)}: $currency - ${"Cities".tr(context)}: $cities",
                                    style: const TextStyle(
                                      color: AppTheme.mutedText,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 10),
                            Container(
                              width: 24,
                              height: 24,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: selected
                                    ? const Color(0xFF2B5FB7)
                                    : const Color(0xFFE2E6EF),
                              ),
                              child: Icon(
                                selected ? Icons.check_rounded : Icons.circle,
                                color: Colors.white,
                                size: selected ? 18 : 8,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: selectedCity.trim().isEmpty ? null : selectedCity,
                decoration: InputDecoration(
                  labelText: "City".tr(context),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                items: (selectedCountry.trim().isEmpty
                        ? const <String>[]
                        : (_countryCitiesList[selectedCountry] ?? const <String>[]))
                    .map(
                      (city) => DropdownMenuItem<String>(
                        value: city,
                        child: Text(city.tr(context)),
                      ),
                    )
                    .toList(),
                onChanged: selectedCountry.trim().isEmpty
                    ? null
                    : (value) {
                        setState(() => selectedCity = (value ?? "").trim());
                      },
              ),
              AppButton(
                text: "Continue".tr(context),
                onPressed: active.trim().isEmpty || selectedCity.trim().isEmpty
                      ? null
                      : () async {
                        await ref
                            .read(appRegionProvider.notifier)
                            .setRegion(country: active, city: selectedCity);
                        if (!context.mounted) return;
                        context.go("/login");
                      },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
