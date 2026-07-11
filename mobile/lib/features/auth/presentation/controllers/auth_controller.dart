import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/storage/secure_storage_service.dart';
import '../../data/datasources/auth_api.dart';
import '../../data/models/user_model.dart';
import '../../data/repositories/auth_repository_impl.dart';
import '../../domain/entities/user.dart';
import '../../domain/usecases/login_user.dart';
import '../../domain/usecases/register_user.dart';

enum AuthStatus {
  unknown,
  authenticated,
  unauthenticated,
}

class AuthState {
  final bool isLoading;
  final AuthStatus status;
  final User? user;
  final String? errorMessage;

  const AuthState({
    this.isLoading = false,
    this.status = AuthStatus.unknown,
    this.user,
    this.errorMessage,
  });

  AuthState copyWith({
    bool? isLoading,
    AuthStatus? status,
    User? user,
    String? errorMessage,
    bool clearError = false,
    bool clearUser = false,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      status: status ?? this.status,
      user: clearUser ? null : (user ?? this.user),
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController();
});

class AuthController extends StateNotifier<AuthState> {
  AuthController() : super(const AuthState());

  final _storage = SecureStorageService();
  final _streamController = StreamController<AuthState>.broadcast();

  @override
  Stream<AuthState> get stream => _streamController.stream;

  void _emit(AuthState newState) {
    state = newState;
    _streamController.add(newState);
  }

  AuthRepositoryImpl _repository() {
    return AuthRepositoryImpl(
      AuthApi(
        ApiClient(storageService: _storage),
      ),
    );
  }

  Future<void> bootstrap() async {
    _emit(state.copyWith(
      isLoading: true,
      status: AuthStatus.unknown,
      clearError: true,
    ));

    try {
      final storedUserJson = await _storage.getCustomerJson();
      final accessToken = await _storage.getAccessToken();

      if (storedUserJson == null ||
          accessToken == null ||
          accessToken.isEmpty) {
        _emit(state.copyWith(
          isLoading: false,
          status: AuthStatus.unauthenticated,
          clearUser: true,
        ));
        return;
      }

      final cachedUser = UserModel.fromJson(storedUserJson);

      try {
        final freshUser = await _repository().getCurrentUser();
        await _storage.saveCustomerJson((freshUser as UserModel).toJson());
        _emit(state.copyWith(
          isLoading: false,
          status: AuthStatus.authenticated,
          user: freshUser,
          clearError: true,
        ));
      } catch (_) {
        _emit(state.copyWith(
          isLoading: false,
          status: AuthStatus.authenticated,
          user: cachedUser,
          clearError: true,
        ));
      }
    } catch (e) {
      _emit(state.copyWith(
        isLoading: false,
        status: AuthStatus.unauthenticated,
        clearUser: true,
        errorMessage: _friendlyErrorMessage(e),
      ));
    }
  }

  Future<bool> login(
    String email,
    String password, {
    bool rememberCredentials = false,
    bool enableBiometric = false,
  }) async {
    _emit(state.copyWith(
      isLoading: true,
      clearError: true,
    ));

    try {
      final result = await LoginUser(_repository()).call(email, password);

      await _storage.saveAccessToken(result.accessToken);
      await _storage.saveRefreshToken(result.refreshToken);
      await _storage.saveCustomerJson((result.user as UserModel).toJson());
      if (rememberCredentials) {
        await _storage.saveString(AppConstants.rememberedEmailKey, email);
        await _storage.saveString(AppConstants.rememberedPasswordKey, password);
      } else {
        await _storage.saveString(AppConstants.rememberedEmailKey, "");
        await _storage.saveString(AppConstants.rememberedPasswordKey, "");
      }
      await _storage.saveBool(AppConstants.biometricEnabledKey, enableBiometric);

      _emit(state.copyWith(
        isLoading: false,
        status: AuthStatus.authenticated,
        user: result.user,
        clearError: true,
      ));
      return true;
    } catch (e) {
      _emit(state.copyWith(
        isLoading: false,
        status: AuthStatus.unauthenticated,
        clearUser: true,
        errorMessage: _friendlyErrorMessage(e),
      ));
      return false;
    }
  }

  Future<bool> quickUnlockWithBiometricScaffold() async {
    final enabled = await _storage.getBool(AppConstants.biometricEnabledKey, defaultValue: false);
    if (!enabled) return false;
    final rememberedEmail = await _storage.getString(AppConstants.rememberedEmailKey) ?? "";
    final rememberedPassword = await _storage.getString(AppConstants.rememberedPasswordKey) ?? "";
    if (rememberedEmail.trim().isEmpty || rememberedPassword.trim().isEmpty) {
      return false;
    }
    return login(
      rememberedEmail.trim(),
      rememberedPassword,
      rememberCredentials: true,
      enableBiometric: true,
    );
  }

  Future<bool> register(String name, String email, String password) async {
    _emit(state.copyWith(
      isLoading: true,
      clearError: true,
    ));

    try {
      final preferredCountry =
          (await _storage.getString(AppConstants.selectedCountryKey) ?? "").trim();
      final result =
          await RegisterUser(_repository()).call(
        name,
        email,
        password,
        preferredCountry: preferredCountry,
      );

      await _storage.saveAccessToken(result.accessToken);
      await _storage.saveRefreshToken(result.refreshToken);
      await _storage.saveCustomerJson((result.user as UserModel).toJson());

      _emit(state.copyWith(
        isLoading: false,
        status: AuthStatus.authenticated,
        user: result.user,
        clearError: true,
      ));
      return true;
    } catch (e) {
      _emit(state.copyWith(
        isLoading: false,
        status: AuthStatus.unauthenticated,
        clearUser: true,
        errorMessage: _friendlyErrorMessage(e),
      ));
      return false;
    }
  }

  String _friendlyErrorMessage(Object error) {
    if (error is DioException) {
      final status = error.response?.statusCode ?? 0;
      if (status >= 500) {
        return "Server error. Please restart backend and try again.";
      }
      if (status == 401) {
        return "Invalid email or password.";
      }
      if (status == 404) {
        return "Login service not found. Please check backend URL.";
      }
      final data = error.response?.data;
      if (data is Map<String, dynamic> && data.isNotEmpty) {
        final first = data.values.first;
        if (first is List && first.isNotEmpty) {
          return first.first.toString();
        }
        if (first != null) {
          return first.toString();
        }
      }
      if (error.type == DioExceptionType.connectionError) {
        return "Cannot connect to server. Please ensure backend is running.";
      }
      if (error.message != null && error.message!.trim().isNotEmpty) {
        return error.message!;
      }
    }
    return error.toString();
  }

  Future<void> logout() async {
    await _storage.clearSession();
    _emit(state.copyWith(
      isLoading: false,
      status: AuthStatus.unauthenticated,
      clearUser: true,
      clearError: true,
    ));
  }

  @override
  void dispose() {
    _streamController.close();
    super.dispose();
  }
}
