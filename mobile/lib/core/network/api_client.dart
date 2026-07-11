import 'package:dio/dio.dart';

import '../constants/app_constants.dart';
import '../storage/secure_storage_service.dart';
import 'auth_interceptor.dart';

class ApiClient {
  late final Dio dio;

  ApiClient({SecureStorageService? storageService}) {
    final storage = storageService ?? SecureStorageService();

    dio = Dio(
      BaseOptions(
        baseUrl: AppConstants.apiBaseUrl,
        connectTimeout: const Duration(seconds: 20),
        receiveTimeout: const Duration(seconds: 20),
        headers: const {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
      ),
    );

    dio.interceptors.add(AuthInterceptor(storage));
  }

  Future<Response> get(String path) async {
    return dio.get(path);
  }

  Future<Response> post(String path, Map<String, dynamic> data) async {
    return dio.post(path, data: data);
  }

  Future<Response> patch(String path, Map<String, dynamic> data) async {
    return dio.patch(path, data: data);
  }

  Future<Response> delete(String path) async {
    return dio.delete(path);
  }
}