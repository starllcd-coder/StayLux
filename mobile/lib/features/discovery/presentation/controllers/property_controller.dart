import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/datasources/property_api.dart';
import '../../data/repositories/property_repository_impl.dart';
import '../../domain/entities/property.dart';
import '../../domain/usecases/get_properties.dart';
import '../../domain/usecases/search_properties.dart';

class DiscoveryFilters {
  final String country;
  final String city;
  final int guests;
  final double minPrice;
  final double maxPrice;
  final double minRating;
  final String businessType;
  final String lifestyle;
  final String amenities;

  const DiscoveryFilters({
    this.country = "",
    this.city = "",
    this.guests = 0,
    this.minPrice = 0,
    this.maxPrice = 0,
    this.minRating = 0,
    this.businessType = "",
    this.lifestyle = "",
    this.amenities = "",
  });

  DiscoveryFilters copyWith({
    String? country,
    String? city,
    int? guests,
    double? minPrice,
    double? maxPrice,
    double? minRating,
    String? businessType,
    String? lifestyle,
    String? amenities,
    bool clearBusinessType = false,
    bool clearLifestyle = false,
    bool clearAmenities = false,
  }) {
    return DiscoveryFilters(
      country: country ?? this.country,
      city: city ?? this.city,
      guests: guests ?? this.guests,
      minPrice: minPrice ?? this.minPrice,
      maxPrice: maxPrice ?? this.maxPrice,
      minRating: minRating ?? this.minRating,
      businessType: clearBusinessType ? "" : (businessType ?? this.businessType),
      lifestyle: clearLifestyle ? "" : (lifestyle ?? this.lifestyle),
      amenities: clearAmenities ? "" : (amenities ?? this.amenities),
    );
  }
}

class PropertyState {
  final bool isLoading;
  final List<Property> properties;
  final String query;
  final DiscoveryFilters filters;
  final List<String> recentSearches;
  final List<String> suggestions;
  final List<Property> recommendedProperties;
  final List<Property> recentlyViewed;
  final String preset;
  final String? error;

  const PropertyState({
    this.isLoading = false,
    this.properties = const [],
    this.query = "",
    this.filters = const DiscoveryFilters(),
    this.recentSearches = const [],
    this.suggestions = const [],
    this.recommendedProperties = const [],
    this.recentlyViewed = const [],
    this.preset = "",
    this.error,
  });

  PropertyState copyWith({
    bool? isLoading,
    List<Property>? properties,
    String? query,
    DiscoveryFilters? filters,
    List<String>? recentSearches,
    List<String>? suggestions,
    List<Property>? recommendedProperties,
    List<Property>? recentlyViewed,
    String? preset,
    String? error,
    bool clearError = false,
  }) {
    return PropertyState(
      isLoading: isLoading ?? this.isLoading,
      properties: properties ?? this.properties,
      query: query ?? this.query,
      filters: filters ?? this.filters,
      recentSearches: recentSearches ?? this.recentSearches,
      suggestions: suggestions ?? this.suggestions,
      recommendedProperties: recommendedProperties ?? this.recommendedProperties,
      recentlyViewed: recentlyViewed ?? this.recentlyViewed,
      preset: preset ?? this.preset,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

final propertyControllerProvider =
    StateNotifierProvider<PropertyController, PropertyState>((ref) {
  return PropertyController();
});

class PropertyController extends StateNotifier<PropertyState> {
  PropertyController() : super(const PropertyState()) {
    loadProperties();
  }

  final PropertyRepositoryImpl _repository =
      PropertyRepositoryImpl(PropertyApi(ApiClient()));
  int _requestVersion = 0;

  Future<void> loadProperties() async {
    final requestVersion = ++_requestVersion;
    state = state.copyWith(
      isLoading: true,
      clearError: true,
    );

    try {
      final f = state.filters;
      final items = await GetProperties(_repository).call(
        country: f.country,
        city: f.city,
        businessType: f.businessType,
        lifestyle: f.lifestyle,
        amenities: f.amenities,
        guests: f.guests > 0 ? f.guests : null,
        minPrice: f.minPrice > 0 ? f.minPrice : null,
        maxPrice: f.maxPrice > 0 ? f.maxPrice : null,
        minRating: f.minRating > 0 ? f.minRating : null,
      );
      final recommended = await _repository.api.getRecommendedProperties();
      if (requestVersion != _requestVersion) return;
      state = state.copyWith(
        isLoading: false,
        properties: items,
        recommendedProperties: recommended,
        clearError: true,
      );
    } catch (e) {
      if (requestVersion != _requestVersion) return;
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> search(String query) async {
    final requestVersion = ++_requestVersion;
    state = state.copyWith(
      isLoading: true,
      query: query,
      clearError: true,
    );

    try {
      final f = state.filters;
      final items = query.trim().isEmpty
          ? await GetProperties(_repository).call(
              country: f.country,
              city: f.city,
              businessType: f.businessType,
              lifestyle: f.lifestyle,
              amenities: f.amenities,
              guests: f.guests > 0 ? f.guests : null,
              minPrice: f.minPrice > 0 ? f.minPrice : null,
              maxPrice: f.maxPrice > 0 ? f.maxPrice : null,
              minRating: f.minRating > 0 ? f.minRating : null,
            )
          : await SearchProperties(_repository).call(
              query,
              // Text search should be global; do not hard-lock by active location filters.
              country: "",
              city: "",
              businessType: f.businessType,
              lifestyle: f.lifestyle,
              amenities: f.amenities,
              guests: f.guests > 0 ? f.guests : null,
              minPrice: f.minPrice > 0 ? f.minPrice : null,
              maxPrice: f.maxPrice > 0 ? f.maxPrice : null,
              minRating: f.minRating > 0 ? f.minRating : null,
            );

      final normalized = query.trim();
      final updatedRecent = normalized.isEmpty
          ? state.recentSearches
          : [
              normalized,
              ...state.recentSearches.where((item) => item.toLowerCase() != normalized.toLowerCase()),
            ].take(6).toList();

      if (requestVersion != _requestVersion) return;
      state = state.copyWith(
        isLoading: false,
        properties: items,
        recentSearches: updatedRecent,
        suggestions: const [],
        clearError: true,
      );
    } catch (e) {
      if (requestVersion != _requestVersion) return;
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> loadSuggestions(String query) async {
    final q = query.trim();
    if (q.length < 2) {
      state = state.copyWith(suggestions: const []);
      return;
    }
    try {
      final list = await _repository.api.getSearchSuggestions(q);
      state = state.copyWith(suggestions: list.take(8).toList());
    } catch (_) {
      state = state.copyWith(suggestions: const []);
    }
  }

  Future<void> updateQuickFilters({
    String? country,
    String? city,
    int? guests,
    double? minPrice,
    double? maxPrice,
    double? minRating,
    String? businessType,
    String? lifestyle,
    String? amenities,
  }) async {
    state = state.copyWith(
      filters: state.filters.copyWith(
        guests: guests,
        country: country,
        city: city,
        minPrice: minPrice,
        maxPrice: maxPrice,
        minRating: minRating,
        businessType: businessType,
        lifestyle: lifestyle,
        amenities: amenities,
      ),
    );
    await search(state.query);
  }

  void recordViewedProperty(Property property) {
    final withoutDup = state.recentlyViewed.where((p) => p.id != property.id).toList();
    final updated = [property, ...withoutDup].take(8).toList();
    state = state.copyWith(recentlyViewed: updated);
  }

  Future<void> applyPreset(String preset) async {
    if (preset == state.preset) {
      state = state.copyWith(
        preset: "",
        filters: state.filters.copyWith(
          guests: 0,
          minPrice: 0,
          maxPrice: 0,
          minRating: 0,
          businessType: "",
          lifestyle: "",
          amenities: "",
          clearBusinessType: true,
          clearLifestyle: true,
          clearAmenities: true,
        ),
      );
      await search(state.query);
      return;
    }

    DiscoveryFilters next = state.filters.copyWith(
      guests: 0,
      minPrice: 0,
      maxPrice: 0,
      minRating: 0,
      businessType: "",
      lifestyle: "",
      amenities: "",
      clearBusinessType: true,
      clearLifestyle: true,
      clearAmenities: true,
    );
    if (preset == "family") {
      next = next.copyWith(guests: 4, lifestyle: "family");
    } else if (preset == "business") {
      next = next.copyWith(businessType: "hotel", minPrice: 40, maxPrice: 180, lifestyle: "business", minRating: 4.0);
    } else if (preset == "luxury") {
      next = next.copyWith(minPrice: 120, lifestyle: "luxury", minRating: 4.0);
    }

    state = state.copyWith(preset: preset, filters: next);
    await search(state.query);
  }

  Future<void> resetFilters({bool clearQuery = false}) async {
    state = state.copyWith(
      preset: "",
      filters: const DiscoveryFilters(),
    );
    await search(clearQuery ? "" : state.query);
  }
}
