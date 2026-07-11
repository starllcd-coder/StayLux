import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/region/app_region_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/utils/gcc_region.dart';
import '../../../../core/widgets/app_button.dart';
import '../../../../core/widgets/app_loader.dart';
import '../../../discovery/presentation/widgets/property_card.dart';
import '../../domain/entities/unit.dart';
import '../../../wishlist/presentation/controllers/wishlist_controller.dart';
import '../controllers/property_details_controller.dart';
import '../widgets/unit_card.dart';

class PropertyDetailsPage extends ConsumerStatefulWidget {
  final int propertyId;

  const PropertyDetailsPage({
    super.key,
    required this.propertyId,
  });

  @override
  ConsumerState<PropertyDetailsPage> createState() => _PropertyDetailsPageState();
}

class _PropertyDetailsPageState extends ConsumerState<PropertyDetailsPage> {
  int galleryIndex = 0;
  bool showMapPreview = false;

  void _bookBestAvailable(PropertyDetailsState state) {
    if (state.property == null || state.units.isEmpty) return;
    final property = state.property!;
    final unit = state.units.first;
    context.push(
      "/booking",
      extra: {
        "unitId": unit.id,
        "propertyName": property.name,
        "unitCode": unit.code,
        "propertyCountry": property.country,
      },
    );
  }

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(wishlistControllerProvider.notifier).load());
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(propertyDetailsControllerProvider(widget.propertyId));
    final wishlistState = ref.watch(wishlistControllerProvider);
    final appRegion = ref.watch(appRegionProvider);

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      bottomNavigationBar: state.property != null && state.units.isNotEmpty
          ? SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x22000000),
                        blurRadius: 18,
                        offset: Offset(0, 8),
                      ),
                    ],
                  ),
                  child: AppButton(
                    text: "Book Best Available".tr(context),
                    onPressed: () => _bookBestAvailable(state),
                  ),
                ),
              ),
            )
          : null,
      body: Builder(
        builder: (_) {
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

          final property = state.property;
          if (property == null) {
            return Center(
              child: Text("Property not found.".tr(context)),
            );
          }

          final isWishlisted = wishlistState.items.any((item) => item.propertyId == property.id);

          return CustomScrollView(
            slivers: [
              SliverAppBar(
                expandedHeight: 260,
                pinned: true,
                backgroundColor: AppTheme.primaryNavy,
                actions: [
                  IconButton(
                    onPressed: () async {
                      await ref.read(wishlistControllerProvider.notifier).toggle(property.id);
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            isWishlisted
                                ? "Removed from wishlist".tr(context)
                                : "Added to wishlist".tr(context),
                          ),
                        ),
                      );
                    },
                    icon: Icon(
                      isWishlisted
                          ? Icons.favorite_rounded
                          : Icons.favorite_border_rounded,
                    ),
                  ),
                ],
                flexibleSpace: FlexibleSpaceBar(
                  title: Text(
                    property.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  background: Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          AppTheme.primaryNavy,
                          Color(0xFF314660),
                        ],
                      ),
                    ),
                    child: Center(
                      child: Icon(
                        Icons.apartment_rounded,
                        size: 64,
                        color: Colors.white.withValues(alpha: 0.85),
                      ),
                    ),
                  ),
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "${property.city.tr(context)}, ${property.country.tr(context)}",
                        style: const TextStyle(
                          color: AppTheme.mutedText,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        property.address,
                        style: const TextStyle(
                          color: AppTheme.darkText,
                          height: 1.5,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          const Icon(Icons.phone_outlined, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              property.phone.isEmpty
                                  ? "No phone".tr(context)
                                  : property.phone,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Icon(Icons.email_outlined, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              property.email.isEmpty
                                  ? "No email".tr(context)
                                  : property.email,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),
                      Text(
                        property.minPrice != null
                            ? "${"From".tr(context)} ${property.currency} ${property.minPrice!.toStringAsFixed(0)} / ${"night".tr(context)}"
                            : "Pricing unavailable".tr(context),
                        style: const TextStyle(
                          color: AppTheme.primaryNavy,
                          fontWeight: FontWeight.w800,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => context.push("/reviews/${property.id}"),
                              icon: const Icon(Icons.star_outline_rounded),
                              label: Text("Reviews".tr(context)),
                              style: OutlinedButton.styleFrom(
                                foregroundColor: AppTheme.primaryNavy,
                                side: const BorderSide(color: AppTheme.primaryNavy),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _BadgeChip(
                            icon: Icons.verified_user_outlined,
                            label: "Verified Property",
                          ),
                          _BadgeChip(
                            icon: Icons.payments_outlined,
                            label: "Transparent Pricing",
                          ),
                          _BadgeChip(
                            icon: Icons.support_agent_outlined,
                            label: "24/7 Support",
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        "Virtual Tour Preview".tr(context),
                        style: TextStyle(
                          color: AppTheme.darkText,
                          fontWeight: FontWeight.w800,
                          fontSize: 17,
                        ),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 180,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(14),
                          child: PageView(
                            onPageChanged: (i) => setState(() => galleryIndex = i),
                            children: [
                              _MediaSlide(
                                icon: Icons.panorama_rounded,
                                title: "Gallery View",
                                subtitle: "Swipe through highlights",
                              ),
                              _MediaSlide(
                                icon: Icons.videocam_outlined,
                                title: "Video Walkthrough",
                                subtitle: property.videoUrl.trim().isNotEmpty
                                    ? property.videoUrl
                                    : "Room and amenity overview",
                              ),
                              _MediaSlide(
                                icon: Icons.threed_rotation,
                                title: "3D Tour",
                                subtitle: property.virtualTourUrl.trim().isNotEmpty
                                    ? property.virtualTourUrl
                                    : "Interactive tour placeholder",
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: List.generate(
                          3,
                          (i) => Container(
                            margin: const EdgeInsets.symmetric(horizontal: 3),
                            width: galleryIndex == i ? 16 : 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: galleryIndex == i ? AppTheme.luxuryGold : const Color(0xFFD9D4C7),
                              borderRadius: BorderRadius.circular(20),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      Text(
                        "Why guests love this property".tr(context),
                        style: TextStyle(
                          color: AppTheme.darkText,
                          fontWeight: FontWeight.w800,
                          fontSize: 17,
                        ),
                      ),
                      const SizedBox(height: 8),
                      _ReasonBullet(
                        "${"Prime location in".tr(context)} ${property.city.tr(context)} ${"with easy access to key destinations.".tr(context)}",
                      ),
                      _ReasonBullet(
                        "Comfort-focused units with modern amenities and reliable service.",
                      ),
                      _ReasonBullet(
                        "Value-for-money pricing with clear taxes, fees, and policies.",
                      ),
                      const SizedBox(height: 6),
                      Text(
                        "${state.peopleViewingNow} ${"people viewing this property now".tr(context)}",
                        style: const TextStyle(color: AppTheme.mutedText, fontSize: 12),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        "Nearby highlights".tr(context),
                        style: TextStyle(
                          color: AppTheme.darkText,
                          fontWeight: FontWeight.w800,
                          fontSize: 17,
                        ),
                      ),
                      const SizedBox(height: 8),
                      _ReasonBullet("City center access and transport links"),
                      _ReasonBullet("Dining, shopping, and local attractions"),
                      _ReasonBullet("Business and leisure friendly neighborhood"),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          ChoiceChip(
                            label: Text("List".tr(context)),
                            selected: !showMapPreview,
                            onSelected: (_) => setState(() => showMapPreview = false),
                          ),
                          const SizedBox(width: 8),
                          ChoiceChip(
                            label: Text("Map".tr(context)),
                            selected: showMapPreview,
                            onSelected: (_) => setState(() => showMapPreview = true),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Container(
                        width: double.infinity,
                        height: 240,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFE6DED0)),
                        ),
                        child: showMapPreview
                            ? Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    "Map Preview".tr(context),
                                    style: const TextStyle(fontWeight: FontWeight.w700),
                                  ),
                                  const SizedBox(height: 6),
                                  Expanded(
                                    child: (property.latitude != null && property.longitude != null)
                                        ? ClipRRect(
                                            borderRadius: BorderRadius.circular(10),
                                            child: FlutterMap(
                                              options: MapOptions(
                                                initialCenter: LatLng(
                                                  property.latitude!,
                                                  property.longitude!,
                                                ),
                                                initialZoom: 13,
                                              ),
                                              children: [
                                                TileLayer(
                                                  urlTemplate: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                                                  userAgentPackageName: "com.staylux.mobile",
                                                ),
                                                MarkerLayer(
                                                  markers: [
                                                    Marker(
                                                      point: LatLng(property.latitude!, property.longitude!),
                                                      width: 40,
                                                      height: 40,
                                                      child: const Icon(Icons.location_on, color: Colors.red),
                                                    ),
                                                  ],
                                                ),
                                              ],
                                            ),
                                          )
                                        : Center(
                                            child: Text(
                                              "Location coordinates unavailable".tr(context),
                                            ),
                                          ),
                                  ),
                                  if (property.latitude != null && property.longitude != null)
                                    TextButton(
                                      onPressed: () async {
                                        final mapsUrl =
                                            "https://www.google.com/maps/search/?api=1&query=${property.latitude},${property.longitude}";
                                        await Clipboard.setData(ClipboardData(text: mapsUrl));
                                        if (!context.mounted) return;
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            content: Text("Map link copied".tr(context)),
                                          ),
                                        );
                                      },
                                      child: Text("Copy Google Maps Link".tr(context)),
                                    ),
                                  Text(
                                    "Interactive map enabled via OpenStreetMap tiles."
                                        .tr(context),
                                    style: TextStyle(color: AppTheme.mutedText, fontSize: 12),
                                  ),
                                ],
                              )
                            : Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text("Nearby".tr(context), style: const TextStyle(fontWeight: FontWeight.w700)),
                                  const SizedBox(height: 6),
                                  Text("- ${"City Center".tr(context)}: 8 ${"min".tr(context)}"),
                                  Text("- ${"Airport".tr(context)}: 18 ${"min".tr(context)}"),
                                  Text("- ${"Marina Mall".tr(context)}: 10 ${"min".tr(context)}"),
                                ],
                              ),
                      ),
                      const SizedBox(height: 20),
                      Text(
                        "Price comparison calendar".tr(context),
                        style: TextStyle(
                          color: AppTheme.darkText,
                          fontWeight: FontWeight.w800,
                          fontSize: 17,
                        ),
                      ),
                      const SizedBox(height: 8),
                      _PriceCalendar(
                        units: state.units,
                        fallbackCountry: property.country.trim().isNotEmpty
                            ? property.country
                            : appRegion.country,
                      ),
                      const SizedBox(height: 26),
                      Text(
                        "Available Units".tr(context),
                        style: TextStyle(
                          color: AppTheme.darkText,
                          fontWeight: FontWeight.w800,
                          fontSize: 18,
                        ),
                      ),
                      const SizedBox(height: 14),
                      if (state.units.isEmpty)
                        Text(
                          "No units available.".tr(context),
                          style: TextStyle(color: AppTheme.mutedText),
                        )
                      else
                        ...state.units.map(
                          (unit) => Column(
                            children: [
                              UnitCard(unit: unit),
                              const SizedBox(height: 10),
                              AppButton(
                                text: "Book This Unit".tr(context),
                                onPressed: () {
                                  context.push(
                                    "/booking",
                                    extra: {
                                      "unitId": unit.id,
                                      "propertyName": property.name,
                                      "unitCode": unit.code,
                                      "propertyCountry": property.country,
                                    },
                                  );
                                },
                              ),
                              const SizedBox(height: 16),
                            ],
                          ),
                        ),
                      if (state.similarProperties.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        Text(
                          "Similar properties".tr(context),
                          style: TextStyle(
                            color: AppTheme.darkText,
                            fontWeight: FontWeight.w800,
                            fontSize: 18,
                          ),
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          height: 230,
                          child: ListView.builder(
                            scrollDirection: Axis.horizontal,
                            itemCount: state.similarProperties.length,
                            itemBuilder: (context, index) {
                              return SizedBox(
                                width: 270,
                                child: PropertyCard(
                                  property: state.similarProperties[index],
                                  compact: true,
                                  onTap: () => context.push("/property/${state.similarProperties[index].id}"),
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _MediaSlide extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _MediaSlide({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 2),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        gradient: const LinearGradient(colors: [Color(0xFF15325A), Color(0xFF2E4A73)]),
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white, size: 30),
            const SizedBox(height: 8),
            Text(
              title.tr(context),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle.tr(context),
              style: const TextStyle(color: Color(0xFFE7E2D6), fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _PriceCalendar extends StatelessWidget {
  final List<Unit> units;
  final String fallbackCountry;

  const _PriceCalendar({
    required this.units,
    required this.fallbackCountry,
  });

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final nightly = units.isNotEmpty ? (units.first.nightlyPrice ?? 0.0) : 0.0;
    final currency = units.isNotEmpty
        ? units.first.currency.toString()
        : currencyForCountry(fallbackCountry);

    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemBuilder: (context, index) {
          final date = now.add(Duration(days: index));
          final isWeekend = date.weekday >= DateTime.friday;
          final price = nightly <= 0 ? 0.0 : (isWeekend ? nightly * 1.08 : nightly);
          return Container(
            width: 92,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: isWeekend ? const Color(0xFFD8C08B) : const Color(0xFFE8E2D4)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("${date.day}/${date.month}", style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                Text(
                  price <= 0 ? "-" : "$currency ${price.toStringAsFixed(0)}",
                  style: const TextStyle(fontSize: 12),
                ),
                const Spacer(),
                Text(
                  (isWeekend ? "Weekend" : "Weekday").tr(context),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10, color: AppTheme.mutedText),
                ),
              ],
            ),
          );
        },
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemCount: 8,
      ),
    );
  }
}

class _BadgeChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _BadgeChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: const Color(0xFFE6DED0)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: AppTheme.primaryNavy),
          const SizedBox(width: 6),
          Text(
            label.tr(context),
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _ReasonBullet extends StatelessWidget {
  final String text;

  const _ReasonBullet(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 2),
            child: Icon(Icons.check_circle_outline, size: 16, color: AppTheme.primaryNavy),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text.tr(context),
              style: const TextStyle(color: AppTheme.darkText, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}
