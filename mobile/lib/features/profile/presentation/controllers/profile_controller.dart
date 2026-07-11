import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/datasources/profile_api.dart';
import '../../data/repositories/profile_repository_impl.dart';
import '../../domain/entities/profile.dart';
import '../../domain/usecases/get_profile.dart';
import '../../domain/usecases/update_profile.dart';

class ProfileState {
  final bool isLoading;
  final bool isSubmitting;
  final CustomerProfile? profile;
  final String? error;

  const ProfileState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.profile,
    this.error,
  });

  ProfileState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    CustomerProfile? profile,
    String? error,
    bool clearError = false,
  }) {
    return ProfileState(
      isLoading: isLoading ?? this.isLoading,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      profile: profile ?? this.profile,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

final profileControllerProvider =
    StateNotifierProvider<ProfileController, ProfileState>((ref) {
  return ProfileController();
});

class ProfileController extends StateNotifier<ProfileState> {
  ProfileController() : super(const ProfileState());

  final _repository = ProfileRepositoryImpl(ProfileApi(ApiClient()));

  Future<void> load() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final profile = await GetProfile(_repository).call();
      state = state.copyWith(
        isLoading: false,
        profile: profile,
        clearError: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<bool> update({
    required String fullName,
    required String email,
    required String mobile,
    required String preferredLanguage,
    required String preferredCountry,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      final profile = await UpdateProfile(_repository).call(
        fullName: fullName,
        email: email,
        mobile: mobile,
        preferredLanguage: preferredLanguage,
        preferredCountry: preferredCountry,
      );
      state = state.copyWith(
        isSubmitting: false,
        profile: profile,
        clearError: true,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: e.toString(),
      );
      return false;
    }
  }

  Future<bool> createTraveler({
    required String fullName,
    required String phone,
    required String whatsapp,
    required String email,
    required String nationality,
    required String idType,
    required String idNumber,
    required String idExpiry,
    required String address,
    required String notes,
    required bool isDefault,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      await _repository.createTraveler(
        fullName: fullName,
        phone: phone,
        whatsapp: whatsapp,
        email: email,
        nationality: nationality,
        idType: idType,
        idNumber: idNumber,
        idExpiry: idExpiry,
        address: address,
        notes: notes,
        isDefault: isDefault,
      );

      final profile = await GetProfile(_repository).call();
      state = state.copyWith(
        isSubmitting: false,
        profile: profile,
        clearError: true,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: e.toString(),
      );
      return false;
    }
  }

  Future<bool> deleteTraveler(int travelerId) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      await _repository.deleteTraveler(travelerId);
      final profile = await GetProfile(_repository).call();
      state = state.copyWith(
        isSubmitting: false,
        profile: profile,
        clearError: true,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: e.toString(),
      );
      return false;
    }
  }
}