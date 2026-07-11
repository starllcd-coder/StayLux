import 'package:dio/dio.dart';

import '../storage/secure_storage_service.dart';

class AuthInterceptor extends Interceptor {
  final SecureStorageService storage;

  AuthInterceptor(this.storage);

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await storage.getAccessToken();

    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }

    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final statusCode = err.response?.statusCode ?? 0;
    final request = err.requestOptions;

    if (statusCode != 401 || request.extra["retried_401"] == true) {
      handler.next(err);
      return;
    }

    final refreshToken = await storage.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      handler.next(err);
      return;
    }

    try {
      final refreshUrl = _buildRefreshUrl(request.baseUrl);
      final refreshDio = Dio();
      final refreshResponse = await refreshDio.post(
        refreshUrl,
        data: {"refresh": refreshToken},
        options: Options(headers: {"Content-Type": "application/json"}),
      );

      final refreshData = refreshResponse.data;
      final access = refreshData is Map<String, dynamic>
          ? (refreshData["access"] ?? "").toString()
          : "";

      if (access.isEmpty) {
        handler.next(err);
        return;
      }

      await storage.saveAccessToken(access);

      request.headers["Authorization"] = "Bearer $access";
      request.extra["retried_401"] = true;

      final retryDio = Dio(BaseOptions(baseUrl: request.baseUrl));
      final retryResponse = await retryDio.fetch(request);
      handler.resolve(retryResponse);
      return;
    } catch (_) {
      handler.next(err);
      return;
    }
  }

  String _buildRefreshUrl(String baseUrl) {
    final trimmed = baseUrl.trim();
    if (trimmed.endsWith("/api/mobile")) {
      return "${trimmed.substring(0, trimmed.length - "/mobile".length)}/auth/refresh/";
    }
    if (trimmed.endsWith("/api/mobile/")) {
      return "${trimmed.substring(0, trimmed.length - "/mobile/".length)}/auth/refresh/";
    }
    if (trimmed.contains("/api/mobile")) {
      return trimmed.replaceFirst("/api/mobile", "/api/auth/refresh/");
    }
    return "$trimmed/auth/refresh/";
  }
}
