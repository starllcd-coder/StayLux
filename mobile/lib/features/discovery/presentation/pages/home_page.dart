import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/region/app_region_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/utils/gcc_region.dart';
import '../../../../core/widgets/app_loader.dart';
import '../../../../core/widgets/language_toggle_button.dart';
import '../controllers/property_controller.dart';
import '../widgets/property_card.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  final searchController = TextEditingController();
  final destinationController = TextEditingController();
  RangeValues priceRange = const RangeValues(0, 300);
  bool compactCards = false;
  bool showMapMode = false;
  String selectedCountry = "";
  bool _regionDefaultsApplied = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      if (_regionDefaultsApplied) return;
      final region = ref.read(appRegionProvider);
      if (region.hasRegion) {
        destinationController.text = region.country;
        selectedCountry = region.country;
        await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
              country: region.country,
              city: "",
            );
      }
      _regionDefaultsApplied = true;
      if (!mounted) return;
      setState(() {});
    });
  }

  @override
  void dispose() {
    searchController.dispose();
    destinationController.dispose();
    super.dispose();
  }

  Future<void> _applyDestination(WidgetRef ref) async {
    final parsed = parseDestinationInput(destinationController.text);
    final country = parsed.country.trim();
    final city = parsed.city.trim();
    selectedCountry = country;
    await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
          country: country,
          city: city,
        );

    // If strict city/country filtering yields no result (common when legacy
    // properties only have address filled), fallback to text search.
    var latestState = ref.read(propertyControllerProvider);
    if (latestState.properties.isEmpty && (city.isNotEmpty || country.isNotEmpty)) {
      final destinationTerm = [city, country].where((v) => v.isNotEmpty).join(" ");
      if (destinationTerm.isNotEmpty) {
        await ref.read(propertyControllerProvider.notifier).search(destinationTerm);
        latestState = ref.read(propertyControllerProvider);
      }
    }

    // If still empty and guest filter is too restrictive, retry with a sane default.
    if (latestState.properties.isEmpty && latestState.filters.guests > 2) {
      await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
            country: country,
            city: city,
            guests: 2,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Guest filter reset to 2 to widen results.".tr(context))),
        );
      }
    }

    if (!mounted) return;
    setState(() {});
  }

  String _filtersSummary(BuildContext context, String currency, int guests) {
    final guestsLabel = guests > 0
        ? "$guests ${"Guests".tr(context)}"
        : "Any Guests".tr(context);
    return "${"Price".tr(context)} $currency ${priceRange.start.toStringAsFixed(0)}-${priceRange.end.toStringAsFixed(0)}  -  $guestsLabel";
  }

  Future<void> _openFiltersSheet(
    BuildContext context,
    WidgetRef ref,
    String activeCurrency,
    String activeCountry,
    int currentGuests,
    String preset,
    bool highRating,
    bool hasWifi,
  ) async {
    var localRange = priceRange;
    var localGuests = currentGuests;
    var localCompact = compactCards;
    var localMap = showMapMode;
    var localHighRating = highRating;
    var localWifi = hasWifi;
    var localPreset = preset;
    final parsedDestination = parseDestinationInput(destinationController.text);
    var localCountry = activeCountry;
    var localCity = parsedDestination.city;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.cardWhite,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (sheetContext, setModalState) {
            return FractionallySizedBox(
              heightFactor: 0.92,
              child: SafeArea(
                child: Padding(
                  padding: EdgeInsets.fromLTRB(
                    16,
                    16,
                    16,
                    MediaQuery.of(sheetContext).viewInsets.bottom + 12,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "Filters".tr(sheetContext),
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Expanded(
                        child: SingleChildScrollView(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                "Countries".tr(sheetContext),
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.darkText,
                                ),
                              ),
                              const SizedBox(height: 8),
                              SizedBox(
                                height: 42,
                                child: ListView.separated(
                                  scrollDirection: Axis.horizontal,
                                  reverse: Directionality.of(sheetContext) == TextDirection.rtl,
                                  itemBuilder: (context, index) {
                                    final country = gccCountries[index];
                                    final isSelected =
                                        localCountry.toLowerCase() == country.toLowerCase();
                                    return ChoiceChip(
                                      label: Text(country.tr(sheetContext)),
                                      selected: isSelected,
                                      onSelected: (_) {
                                        localCountry = country;
                                        localCity = "";
                                        setModalState(() {});
                                      },
                                    );
                                  },
                                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                                  itemCount: gccCountries.length,
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                "Seasonal collections".tr(sheetContext),
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.darkText,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                children: [
                                  FilterChip(
                                    label: Text("Summer Escapes".tr(sheetContext)),
                                    selected: localPreset == "summer",
                                    onSelected: (selected) {
                                      localPreset = selected ? "summer" : "";
                                      if (selected) {
                                        localRange = const RangeValues(60, 260);
                                        localHighRating = true;
                                      }
                                      setModalState(() {});
                                    },
                                  ),
                                  FilterChip(
                                    label: Text("Family Holidays".tr(sheetContext)),
                                    selected: localPreset == "family",
                                    onSelected: (selected) {
                                      localPreset = selected ? "family" : "";
                                      if (selected) localGuests = 4;
                                      setModalState(() {});
                                    },
                                  ),
                                  FilterChip(
                                    label: Text("Business Essentials".tr(sheetContext)),
                                    selected: localPreset == "business",
                                    onSelected: (selected) {
                                      localPreset = selected ? "business" : "";
                                      if (selected) {
                                        localRange = const RangeValues(40, 180);
                                        localHighRating = true;
                                      }
                                      setModalState(() {});
                                    },
                                  ),
                                  FilterChip(
                                    label: Text("Luxury Retreats".tr(sheetContext)),
                                    selected: localPreset == "luxury",
                                    onSelected: (selected) {
                                      localPreset = selected ? "luxury" : "";
                                      if (selected && localRange.start < 120) {
                                        localRange = RangeValues(120, localRange.end);
                                        localHighRating = true;
                                      }
                                      setModalState(() {});
                                    },
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              Text(
                                "Quick filters".tr(sheetContext),
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.darkText,
                                ),
                              ),
                              const SizedBox(height: 12),
                              Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                children: [
                                  FilterChip(
                                    label: Text("Family Friendly".tr(sheetContext)),
                                    selected: localPreset == "family",
                                    onSelected: (selected) {
                                      localPreset = selected ? "family" : "";
                                      if (selected) localGuests = 4;
                                      setModalState(() {});
                                    },
                                  ),
                                  FilterChip(
                                    label: Text("Business Trip".tr(sheetContext)),
                                    selected: localPreset == "business",
                                    onSelected: (selected) {
                                      localPreset = selected ? "business" : "";
                                      if (selected) localRange = const RangeValues(40, 180);
                                      setModalState(() {});
                                    },
                                  ),
                                  FilterChip(
                                    label: Text("Luxury".tr(sheetContext)),
                                    selected: localPreset == "luxury",
                                    onSelected: (selected) {
                                      localPreset = selected ? "luxury" : "";
                                      if (selected && localRange.start < 120) {
                                        localRange = RangeValues(120, localRange.end);
                                      }
                                      setModalState(() {});
                                    },
                                  ),
                                  FilterChip(
                                    label: Text("4+ Rating".tr(sheetContext)),
                                    selected: localHighRating,
                                    onSelected: (selected) {
                                      localHighRating = selected;
                                      setModalState(() {});
                                    },
                                  ),
                                  FilterChip(
                                    label: Text("Wifi".tr(sheetContext)),
                                    selected: localWifi,
                                    onSelected: (selected) {
                                      localWifi = selected;
                                      setModalState(() {});
                                    },
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              DropdownButtonFormField<int>(
                                initialValue: localGuests,
                                decoration: InputDecoration(
                                  labelText: "Guests".tr(sheetContext),
                                ),
                                items: const [0, 1, 2, 3, 4, 5, 6]
                                    .map(
                                      (g) => DropdownMenuItem(
                                        value: g,
                                        child: Text(
                                          g == 0
                                              ? "Any Guests".tr(sheetContext)
                                              : "$g ${"Guests".tr(sheetContext)}",
                                        ),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (v) {
                                  if (v == null) return;
                                  localGuests = v;
                                  setModalState(() {});
                                },
                              ),
                              const SizedBox(height: 10),
                              Text(
                                "${"Price".tr(sheetContext)}: $activeCurrency ${localRange.start.toStringAsFixed(0)} - ${localRange.end.toStringAsFixed(0)}",
                                style: const TextStyle(color: AppTheme.mutedText),
                              ),
                              RangeSlider(
                                values: localRange,
                                min: 0,
                                max: 500,
                                divisions: 20,
                                labels: RangeLabels(
                                  localRange.start.toStringAsFixed(0),
                                  localRange.end.toStringAsFixed(0),
                                ),
                                onChanged: (v) => setModalState(() => localRange = v),
                              ),
                              SegmentedButton<bool>(
                                segments: [
                                  ButtonSegment(
                                    value: false,
                                    label: Text("List".tr(sheetContext)),
                                    icon: const Icon(Icons.view_agenda_outlined),
                                  ),
                                  ButtonSegment(
                                    value: true,
                                    label: Text("Compact".tr(sheetContext)),
                                    icon: const Icon(Icons.view_compact_outlined),
                                  ),
                                ],
                                selected: {localCompact},
                                onSelectionChanged: (values) =>
                                    setModalState(() => localCompact = values.first),
                              ),
                              const SizedBox(height: 8),
                              SwitchListTile(
                                value: localMap,
                                contentPadding: EdgeInsets.zero,
                                title: Text("Map".tr(sheetContext)),
                                onChanged: (v) => setModalState(() => localMap = v),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.fromLTRB(8, 10, 8, 6),
                        decoration: BoxDecoration(
                          color: AppTheme.cardWhite,
                          borderRadius: BorderRadius.circular(16),
                          boxShadow: const [
                            BoxShadow(
                              color: Color(0x14000000),
                              blurRadius: 18,
                              offset: Offset(0, -4),
                            ),
                          ],
                        ),
                        child: Row(
                          children: [
                            OutlinedButton(
                              onPressed: () async {
                                localRange = const RangeValues(0, 300);
                                localGuests = 0;
                                localHighRating = false;
                                localWifi = false;
                                localPreset = "";
                                localCountry = "";
                                localCity = "";
                                setState(() {
                                  selectedCountry = "";
                                  destinationController.clear();
                                  priceRange = const RangeValues(0, 300);
                                });
                                await ref
                                    .read(propertyControllerProvider.notifier)
                                    .resetFilters(clearQuery: false);
                                if (!sheetContext.mounted) return;
                                setModalState(() {});
                              },
                              child: Text("Reset".tr(sheetContext)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: FilledButton(
                                style: FilledButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(vertical: 14),
                                ),
                                onPressed: () async {
                                  final presetBusinessType =
                                      localPreset == "business" ? "hotel" : "";
                                  final presetLifestyle = switch (localPreset) {
                                    "family" => "family",
                                    "business" => "business",
                                    "luxury" => "luxury",
                                    _ => "",
                                  };
                                  final presetAmenities = switch (localPreset) {
                                    "summer" => "pool",
                                    _ => "",
                                  };
                                  final amenitiesCombined = <String>{
                                    if (presetAmenities.isNotEmpty) presetAmenities,
                                    if (localWifi) "wifi",
                                  }.join(",");

                                  setState(() {
                                    priceRange = localRange;
                                    compactCards = localCompact;
                                    showMapMode = localMap;
                                    selectedCountry = localCountry;
                                    destinationController.text = localCity.trim().isNotEmpty
                                        ? "${localCity.trim()}, ${localCountry.trim()}"
                                        : localCountry.trim();
                                  });
                                  await ref
                                      .read(propertyControllerProvider.notifier)
                                      .updateQuickFilters(
                                        country: localCountry,
                                        city: localCity,
                                        guests: localGuests,
                                        minPrice: localRange.start,
                                        maxPrice: localRange.end,
                                        minRating: localHighRating ? 4.0 : 0,
                                        businessType: presetBusinessType,
                                        lifestyle: presetLifestyle,
                                        amenities: amenitiesCombined,
                                      );
                                  if (!sheetContext.mounted) return;
                                  Navigator.of(sheetContext).pop();
                                },
                                child: Text("Apply".tr(sheetContext)),
                              ),
                            ),
                          ],
                        ),
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
    final isArabic = Directionality.of(context) == TextDirection.rtl;
    final state = ref.watch(propertyControllerProvider);
    final region = ref.watch(appRegionProvider);
    final filters = state.filters;
    final mainPropertyIds = state.properties.map((p) => p.id).toSet();
    final mainPropertySignatures = state.properties
        .map(
          (p) =>
              "${p.name.trim().toLowerCase()}|${p.city.trim().toLowerCase()}|${p.country.trim().toLowerCase()}|${p.address.trim().toLowerCase()}",
        )
        .toSet();
    final recommendedProperties = state.recommendedProperties
        .where(
          (p) =>
              !mainPropertyIds.contains(p.id) &&
              !mainPropertySignatures.contains(
                "${p.name.trim().toLowerCase()}|${p.city.trim().toLowerCase()}|${p.country.trim().toLowerCase()}|${p.address.trim().toLowerCase()}",
              ),
        )
        .toList();
    final recentlyViewedProperties = state.recentlyViewed
        .where(
          (p) =>
              !mainPropertyIds.contains(p.id) &&
              !mainPropertySignatures.contains(
                "${p.name.trim().toLowerCase()}|${p.city.trim().toLowerCase()}|${p.country.trim().toLowerCase()}|${p.address.trim().toLowerCase()}",
              ),
        )
        .toList();
    final destinationCounts = <String, int>{};
    for (final p in state.properties) {
      final city = p.city.trim();
      if (city.isEmpty) continue;
      final country = p.country.trim();
      final key = country.isEmpty ? city : "$city, $country";
      destinationCounts[key] = (destinationCounts[key] ?? 0) + 1;
    }
    final smartDestinations = destinationCounts.keys.take(6).toList();
    final trendingLocations = destinationCounts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final activeCountry = selectedCountry.trim().isEmpty
        ? (filters.country.trim().isNotEmpty ? filters.country.trim() : region.country.trim())
        : selectedCountry.trim();
    final firstCurrency = state.properties
        .map((p) => p.currency.trim())
        .firstWhere((c) => c.isNotEmpty, orElse: () => "");
    final activeCurrency = firstCurrency.isNotEmpty
        ? firstCurrency
        : currencyForCountry(activeCountry);
    final activeFilterChips = <({String label, Future<void> Function() onRemove})>[
      if (filters.country.trim().isNotEmpty)
        (
          label: filters.country.trim().tr(context),
          onRemove: () async {
            await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
                  country: "",
                );
            if (!mounted) return;
            setState(() {
              selectedCountry = "";
              destinationController.text = filters.city.trim();
            });
          },
        ),
      if (filters.city.trim().isNotEmpty)
        (
          label: filters.city.trim().tr(context),
          onRemove: () async {
            await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
                  city: "",
                );
            if (!mounted) return;
            setState(() {
              destinationController.text = filters.country.trim();
            });
          },
        ),
      if (filters.guests > 0)
        (
          label: "${filters.guests} ${"Guests".tr(context)}",
          onRemove: () async {
            await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
                  guests: 0,
                );
            if (!mounted) return;
            setState(() {});
          },
        ),
      if (filters.minRating >= 4)
        (
          label: "4+ ${"Rating".tr(context)}",
          onRemove: () async {
            await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
                  minRating: 0,
                );
            if (!mounted) return;
            setState(() {});
          },
        ),
      if (filters.amenities.toLowerCase().contains("wifi"))
        (
          label: "Wifi".tr(context),
          onRemove: () async {
            final parts = filters.amenities
                .split(",")
                .map((e) => e.trim())
                .where((e) => e.isNotEmpty && e.toLowerCase() != "wifi")
                .toList();
            await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
                  amenities: parts.join(","),
                );
            if (!mounted) return;
            setState(() {});
          },
        ),
      if (state.preset == "family")
        (
          label: "Family Friendly".tr(context),
          onRemove: () async {
            await ref.read(propertyControllerProvider.notifier).applyPreset("family");
            if (!mounted) return;
            setState(() => priceRange = const RangeValues(0, 300));
          },
        ),
      if (state.preset == "business")
        (
          label: "Business Trip".tr(context),
          onRemove: () async {
            await ref.read(propertyControllerProvider.notifier).applyPreset("business");
            if (!mounted) return;
            setState(() => priceRange = const RangeValues(0, 300));
          },
        ),
      if (state.preset == "luxury")
        (
          label: "Luxury".tr(context),
          onRemove: () async {
            await ref.read(propertyControllerProvider.notifier).applyPreset("luxury");
            if (!mounted) return;
            setState(() => priceRange = const RangeValues(0, 300));
          },
        ),
      if (state.preset == "summer")
        (
          label: "Summer Escapes".tr(context),
          onRemove: () async {
            await ref.read(propertyControllerProvider.notifier).resetFilters(clearQuery: false);
            if (!mounted) return;
            setState(() => priceRange = const RangeValues(0, 300));
          },
        ),
    ];
    final hasActiveFilters = activeFilterChips.isNotEmpty;

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "Discover Your Stay".tr(context),
                          style: TextStyle(
                            color: AppTheme.darkText,
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          "Hotels, residences, and luxury stays".tr(context),
                          style: TextStyle(
                            color: AppTheme.mutedText,
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const LanguageToggleButton(width: 100, height: 40),
                  IconButton(
                    onPressed: () => context.push("/notifications"),
                    icon: const Icon(Icons.notifications_none_rounded),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
              child: TextField(
                controller: searchController,
                onChanged: (value) {
                  ref.read(propertyControllerProvider.notifier).search(value);
                  ref.read(propertyControllerProvider.notifier).loadSuggestions(value);
                  setState(() {});
                },
                decoration: InputDecoration(
                  hintText: "Search stays, cities, properties...".tr(context),
                  prefixIcon: const Icon(Icons.search_rounded),
                  suffixIcon: searchController.text.isEmpty
                      ? null
                      : IconButton(
                          onPressed: () {
                            searchController.clear();
                            ref.read(propertyControllerProvider.notifier).search("");
                            ref.read(propertyControllerProvider.notifier).loadSuggestions("");
                            setState(() {});
                          },
                          icon: const Icon(Icons.close_rounded),
                        ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: TextField(
                controller: destinationController,
                textInputAction: TextInputAction.search,
                onChanged: (_) => setState(() {}),
                onSubmitted: (_) => _applyDestination(ref),
                decoration: InputDecoration(
                  hintText:
                      "Destination (City, Country) e.g. Salalah, Oman".tr(context),
                  prefixIcon: const Icon(Icons.location_on_outlined),
                  suffixIcon: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (destinationController.text.trim().isNotEmpty)
                        IconButton(
                          onPressed: () async {
                            destinationController.clear();
                            selectedCountry = "";
                            await ref.read(propertyControllerProvider.notifier).updateQuickFilters(
                                  country: "",
                                  city: "",
                                );
                            if (!mounted) return;
                            setState(() {});
                          },
                          icon: const Icon(Icons.close_rounded),
                        ),
                      IconButton(
                        onPressed: () => _applyDestination(ref),
                        icon: Icon(
                          isArabic ? Icons.arrow_back_rounded : Icons.arrow_forward_rounded,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              ),
            if (state.suggestions.isNotEmpty && searchController.text.trim().isNotEmpty)
              SizedBox(
                height: 42,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  reverse: isArabic,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemBuilder: (context, index) {
                    final s = state.suggestions[index];
                    return ActionChip(
                      label: Text(s),
                      onPressed: () {
                        searchController.text = s;
                        ref.read(propertyControllerProvider.notifier).search(s);
                        ref.read(propertyControllerProvider.notifier).loadSuggestions("");
                        setState(() {});
                      },
                    );
                  },
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemCount: state.suggestions.length,
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _filtersSummary(
                        context,
                        activeCurrency,
                        filters.guests,
                      ),
                      style: const TextStyle(color: AppTheme.mutedText, fontSize: 12),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  ChoiceChip(
                    label: Text(showMapMode ? "Map".tr(context) : "List".tr(context)),
                    selected: showMapMode,
                    onSelected: (selected) {
                      setState(() => showMapMode = selected);
                    },
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    onPressed: () => _openFiltersSheet(
                      context,
                      ref,
                      activeCurrency,
                      activeCountry,
                      filters.guests,
                      state.preset,
                      filters.minRating >= 4,
                      filters.amenities.toLowerCase().contains("wifi"),
                    ),
                    icon: const Icon(Icons.tune_rounded, size: 18),
                    label: Text("Filters".tr(context)),
                  ),
                ],
              ),
            ),
            if (hasActiveFilters)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: activeFilterChips
                          .map(
                            (chip) => InputChip(
                              label: Text(chip.label),
                              onDeleted: () {
                                chip.onRemove();
                              },
                            ),
                          )
                          .toList(),
                    ),
                    const SizedBox(height: 6),
                    Align(
                      alignment: AlignmentDirectional.centerEnd,
                      child: TextButton.icon(
                        onPressed: () async {
                          searchController.clear();
                          destinationController.clear();
                          selectedCountry = "";
                          setState(() {
                            priceRange = const RangeValues(0, 300);
                          });
                          await ref
                              .read(propertyControllerProvider.notifier)
                              .resetFilters(clearQuery: true);
                          if (!mounted) return;
                          setState(() {});
                        },
                        icon: const Icon(Icons.restart_alt_rounded),
                        label: Text("Reset Filters".tr(context)),
                      ),
                    ),
                  ],
                ),
              ),
            if (state.recentSearches.isNotEmpty && searchController.text.trim().isEmpty)
              SizedBox(
                height: 40,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  reverse: isArabic,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemBuilder: (context, index) {
                    final item = state.recentSearches[index];
                    return ActionChip(
                      label: Text(item),
                      onPressed: () {
                        searchController.text = item;
                        ref.read(propertyControllerProvider.notifier).search(item);
                      },
                    );
                  },
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemCount: state.recentSearches.length,
                ),
              ),
            Expanded(
              child: Builder(
                builder: (listContext) {
                  if (state.isLoading) {
                    return const AppLoader();
                  }

                  if (state.error != null) {
                    return Center(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Text(
                          state.error!,
                          textAlign: TextAlign.center,
                        ),
                      ),
                    );
                  }

                  if (state.properties.isEmpty) {
                    return Center(
                      child: Text(
                        "No properties found.".tr(context),
                        style: TextStyle(
                          color: AppTheme.mutedText,
                          fontSize: 15,
                        ),
                      ),
                    );
                  }

                  return RefreshIndicator(
                    onRefresh: () => ref.read(propertyControllerProvider.notifier).loadProperties(),
                    child: ListView(
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 20),
                      children: [
                        if (smartDestinations.isNotEmpty && searchController.text.trim().isEmpty) ...[
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Text(
                              "Smart destination suggestions".tr(context),
                              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                            ),
                          ),
                          SizedBox(
                            height: 40,
                            child: ListView.separated(
                                  scrollDirection: Axis.horizontal,
                                  reverse: Directionality.of(listContext) == TextDirection.rtl,
                                  itemBuilder: (context, index) {
                                final city = smartDestinations[index];
                                return ActionChip(
                                  label: Text(city),
                                  onPressed: () {
                                    final parsed = parseDestinationInput(city);
                                    destinationController.text = city;
                                    selectedCountry = parsed.country;
                                    ref.read(propertyControllerProvider.notifier).updateQuickFilters(
                                          city: parsed.city,
                                          country: parsed.country,
                                        );
                                  },
                                );
                              },
                              separatorBuilder: (_, __) => const SizedBox(width: 8),
                              itemCount: smartDestinations.length,
                            ),
                          ),
                          const SizedBox(height: 8),
                        ],
                        if (trendingLocations.isNotEmpty && searchController.text.trim().isEmpty) ...[
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Text(
                              "Trending locations".tr(context),
                              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                            ),
                          ),
                          SizedBox(
                            height: 84,
                            child: ListView.builder(
                              scrollDirection: Axis.horizontal,
                              itemCount: trendingLocations.length > 8 ? 8 : trendingLocations.length,
                              itemBuilder: (context, index) {
                                final item = trendingLocations[index];
                                return GestureDetector(
                                  onTap: () {
                                    final parsed = parseDestinationInput(item.key);
                                    destinationController.text = item.key;
                                    selectedCountry = parsed.country;
                                    ref.read(propertyControllerProvider.notifier).updateQuickFilters(
                                          city: parsed.city,
                                          country: parsed.country,
                                        );
                                  },
                                  child: Container(
                                    width: 152,
                                    margin: const EdgeInsets.only(right: 10),
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(color: const Color(0xFFE6DED0)),
                                    ),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      children: [
                                        Text(item.key, style: const TextStyle(fontWeight: FontWeight.w700)),
                                        const SizedBox(height: 4),
                                        Text(
                                          "${item.value} ${"stays".tr(context)}",
                                          style: const TextStyle(color: AppTheme.mutedText, fontSize: 12),
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
                          const SizedBox(height: 8),
                        ],
                        if (recommendedProperties.isNotEmpty && searchController.text.trim().isEmpty) ...[
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8, top: 4),
                            child: Text(
                              "Recommended for you".tr(context),
                              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                            ),
                          ),
                          SizedBox(
                            height: 240,
                            child: ListView.builder(
                              scrollDirection: Axis.horizontal,
                              itemCount: recommendedProperties.length,
                              itemBuilder: (context, index) {
                                final property = recommendedProperties[index];
                                return SizedBox(
                                  width: 290,
                                  child: PropertyCard(
                                    property: property,
                                    compact: true,
                                    onTap: () {
                                      ref.read(propertyControllerProvider.notifier).recordViewedProperty(property);
                                      context.push("/property/${property.id}");
                                    },
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                        if (recentlyViewedProperties.isNotEmpty && searchController.text.trim().isEmpty) ...[
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8, top: 10),
                            child: Text(
                              "Recently viewed".tr(context),
                              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                            ),
                          ),
                          SizedBox(
                            height: 220,
                            child: ListView.builder(
                              scrollDirection: Axis.horizontal,
                              itemCount: recentlyViewedProperties.length,
                              itemBuilder: (context, index) {
                                final property = recentlyViewedProperties[index];
                                return SizedBox(
                                  width: 270,
                                  child: PropertyCard(
                                    property: property,
                                    compact: true,
                                    onTap: () {
                                      ref.read(propertyControllerProvider.notifier).recordViewedProperty(property);
                                      context.push("/property/${property.id}");
                                    },
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                        if (showMapMode)
                          AnimatedContainer(
                            duration: const Duration(milliseconds: 250),
                            curve: Curves.easeOut,
                            width: double.infinity,
                            margin: const EdgeInsets.only(bottom: 12, top: 4),
                            height: 260,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: const Color(0xFFE6DED0)),
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(12),
                              child: FlutterMap(
                                options: MapOptions(
                                  initialCenter: LatLng(
                                    (state.properties.first.latitude ?? 23.5880),
                                    (state.properties.first.longitude ?? 58.3829),
                                  ),
                                  initialZoom: 10,
                                ),
                                children: [
                                  TileLayer(
                                    urlTemplate: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                                    userAgentPackageName: "com.staylux.mobile",
                                  ),
                                  MarkerLayer(
                                    markers: state.properties
                                        .where((p) => p.latitude != null && p.longitude != null)
                                        .map(
                                          (p) => Marker(
                                            point: LatLng(p.latitude!, p.longitude!),
                                            width: 34,
                                            height: 34,
                                            child: GestureDetector(
                                              onTap: () => context.push("/property/${p.id}"),
                                              child: const Icon(Icons.location_on, color: Colors.red),
                                            ),
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ...state.properties.map(
                          (property) => showMapMode
                              ? Container(
                                  margin: const EdgeInsets.only(bottom: 8),
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: const Color(0xFFE6DED0)),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.location_on_outlined, color: AppTheme.primaryNavy),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          "${property.name} (${property.latitude ?? 0}, ${property.longitude ?? 0})",
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      TextButton(
                                        onPressed: () {
                                          ref.read(propertyControllerProvider.notifier).recordViewedProperty(property);
                                          context.push("/property/${property.id}");
                                        },
                                        child: Text("Open".tr(context)),
                                      ),
                                    ],
                                  ),
                                )
                              : PropertyCard(
                                  property: property,
                                  compact: compactCards,
                                  onTap: () {
                                    ref.read(propertyControllerProvider.notifier).recordViewedProperty(property);
                                    context.push("/property/${property.id}");
                                  },
                                ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}




