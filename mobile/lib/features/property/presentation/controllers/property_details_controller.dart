import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../../discovery/domain/entities/property.dart';
import '../../data/datasources/property_details_api.dart';
import '../../data/repositories/property_details_repository_impl.dart';
import '../../domain/entities/unit.dart';
import '../../domain/usecases/get_property_details.dart';

class PropertyDetailsState {
  final bool isLoading;
  final Property? property;
  final List<Unit> units;
  final List<Property> similarProperties;
  final int peopleViewingNow;
  final String? error;

  const PropertyDetailsState({
    this.isLoading = false,
    this.property,
    this.units = const [],
    this.similarProperties = const [],
    this.peopleViewingNow = 0,
    this.error,
  });

  PropertyDetailsState copyWith({
    bool? isLoading,
    Property? property,
    List<Unit>? units,
    List<Property>? similarProperties,
    int? peopleViewingNow,
    String? error,
    bool clearError = false,
  }) {
    return PropertyDetailsState(
      isLoading: isLoading ?? this.isLoading,
      property: property ?? this.property,
      units: units ?? this.units,
      similarProperties: similarProperties ?? this.similarProperties,
      peopleViewingNow: peopleViewingNow ?? this.peopleViewingNow,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

final propertyDetailsControllerProvider = StateNotifierProvider.family<
    PropertyDetailsController, PropertyDetailsState, int>((ref, propertyId) {
  return PropertyDetailsController(propertyId);
});

class PropertyDetailsController extends StateNotifier<PropertyDetailsState> {
  PropertyDetailsController(this.propertyId)
      : super(const PropertyDetailsState()) {
    load();
  }

  final int propertyId;
  final _repository =
      PropertyDetailsRepositoryImpl(PropertyDetailsApi(ApiClient()));

  Future<void> load() async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
    );

    try {
      final usecase = GetPropertyDetails(_repository);
      final property = await usecase.property(propertyId);
      final units = await usecase.units(propertyId);
      final similar = await usecase.similar(propertyId);
      final viewing = ((propertyId * 7) % 5) + 2;

      state = state.copyWith(
        isLoading: false,
        property: property,
        units: units,
        similarProperties: similar,
        peopleViewingNow: viewing,
        clearError: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }
}
