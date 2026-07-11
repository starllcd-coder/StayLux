import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../constants/app_constants.dart';
import '../storage/secure_storage_service.dart';
import '../utils/gcc_region.dart';

class AppRegionState {
  final String country;
  final String city;

  const AppRegionState({
    this.country = "",
    this.city = "",
  });

  bool get hasCountry => country.trim().isNotEmpty;
  bool get hasRegion => country.trim().isNotEmpty && city.trim().isNotEmpty;
  String get currency => currencyForCountry(country);

  AppRegionState copyWith({
    String? country,
    String? city,
  }) {
    return AppRegionState(
      country: country ?? this.country,
      city: city ?? this.city,
    );
  }
}

final appRegionProvider =
    StateNotifierProvider<AppRegionController, AppRegionState>((ref) {
  return AppRegionController();
});

class AppRegionController extends StateNotifier<AppRegionState> {
  AppRegionController() : super(const AppRegionState());

  final _storage = SecureStorageService();

  Future<void> bootstrap() async {
    final saved = await _storage.getString(AppConstants.selectedCountryKey) ?? "";
    final savedCity = await _storage.getString(AppConstants.selectedCityKey) ?? "";
    state = state.copyWith(
      country: saved.trim(),
      city: savedCity.trim(),
    );
  }

  Future<void> setCountry(String country) async {
    final clean = country.trim();
    await _storage.saveString(AppConstants.selectedCountryKey, clean);
    state = state.copyWith(country: clean);
  }

  Future<void> setRegion({
    required String country,
    required String city,
  }) async {
    final cleanCountry = country.trim();
    final cleanCity = city.trim();
    await _storage.saveString(AppConstants.selectedCountryKey, cleanCountry);
    await _storage.saveString(AppConstants.selectedCityKey, cleanCity);
    state = state.copyWith(
      country: cleanCountry,
      city: cleanCity,
    );
  }
}
