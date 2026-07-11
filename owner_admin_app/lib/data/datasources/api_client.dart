import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/config/app_config.dart';
import '../../core/network/api_exception.dart';
import '../repositories/token_storage.dart';

class ApiClient {
  final http.Client _http;

  ApiClient({http.Client? httpClient}) : _http = httpClient ?? http.Client();

  Future<Map<String, dynamic>> postJson(
    String path, {
    required Map<String, dynamic> body,
    bool authenticated = false,
    String? bearerToken,
  }) async {
    final response = await _send(
      method: 'POST',
      path: path,
      body: jsonEncode(body),
      authenticated: authenticated,
      bearerToken: bearerToken,
    );
    return _decodeMap(response);
  }

  Future<Map<String, dynamic>> patchJson(
    String path, {
    required Map<String, dynamic> body,
    bool authenticated = true,
    String? bearerToken,
  }) async {
    final response = await _send(
      method: 'PATCH',
      path: path,
      body: jsonEncode(body),
      authenticated: authenticated,
      bearerToken: bearerToken,
    );
    return _decodeMap(response);
  }

  Future<Map<String, dynamic>> getMap(
    String path, {
    bool authenticated = true,
    Map<String, String>? queryParameters,
    String? bearerToken,
  }) async {
    final response = await _send(
      method: 'GET',
      path: path,
      queryParameters: queryParameters,
      authenticated: authenticated,
      bearerToken: bearerToken,
    );
    return _decodeMap(response);
  }

  Future<List<dynamic>> getList(
    String path, {
    bool authenticated = true,
    Map<String, String>? queryParameters,
    String? bearerToken,
  }) async {
    final response = await _send(
      method: 'GET',
      path: path,
      queryParameters: queryParameters,
      authenticated: authenticated,
      bearerToken: bearerToken,
    );
    final decoded = _decodeAny(response);
    if (decoded is List<dynamic>) return decoded;
    if (decoded is Map<String, dynamic> && decoded['results'] is List<dynamic>) {
      return decoded['results'] as List<dynamic>;
    }
    throw const ApiException('Unexpected response format from server');
  }

  Future<http.Response> _send({
    required String method,
    required String path,
    Map<String, String>? queryParameters,
    String? body,
    required bool authenticated,
    String? bearerToken,
    bool retryingAfterRefresh = false,
  }) async {
    final uri = _buildUri(path, queryParameters: queryParameters);
    final headers = await _buildHeaders(
      authenticated: authenticated,
      hasBody: body != null,
      bearerToken: bearerToken,
    );

    late http.Response response;
    switch (method) {
      case 'GET':
        response = await _http.get(uri, headers: headers);
        break;
      case 'POST':
        response = await _http.post(uri, headers: headers, body: body);
        break;
      case 'PATCH':
        response = await _http.patch(uri, headers: headers, body: body);
        break;
      default:
        throw ApiException('Unsupported HTTP method: $method');
    }

    if (response.statusCode == 401 && authenticated && !retryingAfterRefresh) {
      final refreshed = await _refreshToken();
      if (refreshed) {
        return _send(
          method: method,
          path: path,
          queryParameters: queryParameters,
          body: body,
          authenticated: authenticated,
          bearerToken: bearerToken,
          retryingAfterRefresh: true,
        );
      }
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = _extractErrorMessage(response);
      throw ApiException(message, statusCode: response.statusCode);
    }

    return response;
  }

  Uri _buildUri(String path, {Map<String, String>? queryParameters}) {
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    final fullUrl = '${AppConfig.apiBaseUrl}$normalizedPath';
    final uri = Uri.parse(fullUrl);
    if (queryParameters == null || queryParameters.isEmpty) return uri;
    return uri.replace(queryParameters: queryParameters);
  }

  Future<Map<String, String>> _buildHeaders({
    required bool authenticated,
    required bool hasBody,
    String? bearerToken,
  }) async {
    final headers = <String, String>{};
    if (hasBody) {
      headers['Content-Type'] = 'application/json';
    }
    if (authenticated) {
      final token = (bearerToken != null && bearerToken.trim().isNotEmpty)
          ? bearerToken.trim()
          : await TokenStorage.getToken();
      if (token == null || token.isEmpty) {
        throw const ApiException('You are not logged in');
      }
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  dynamic _decodeAny(http.Response response) {
    if (response.body.trim().isEmpty) return {};
    return jsonDecode(response.body);
  }

  Map<String, dynamic> _decodeMap(http.Response response) {
    final decoded = _decodeAny(response);
    if (decoded is Map<String, dynamic>) return decoded;
    throw const ApiException('Unexpected response format from server');
  }

  String _extractErrorMessage(http.Response response) {
    try {
      final decoded = _decodeAny(response);
      if (decoded is Map<String, dynamic>) {
        final detail = decoded['detail'];
        if (detail is String && detail.trim().isNotEmpty) return detail;

        final first = decoded.entries.firstWhere(
          (entry) => entry.value != null && entry.value.toString().trim().isNotEmpty,
          orElse: () => const MapEntry('', ''),
        );
        if (first.key.isNotEmpty) {
          return '${first.key}: ${first.value}';
        }
      }
    } catch (_) {
      // Use fallback below when response is not JSON.
    }
    return 'Request failed (${response.statusCode})';
  }

  Future<bool> _refreshToken() async {
    final refreshToken = await TokenStorage.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return false;

    final uri = _buildUri('/api/auth/refresh/');
    final response = await _http.post(
      uri,
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh': refreshToken}),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      await TokenStorage.clear();
      return false;
    }

    try {
      final decoded = _decodeMap(response);
      final newAccess = decoded['access'] as String?;
      final newRefresh = decoded['refresh'] as String?;
      if (newAccess == null || newAccess.isEmpty) return false;

      await TokenStorage.saveTokens(
        token: newAccess,
        refreshToken: newRefresh ?? refreshToken,
      );
      return true;
    } catch (_) {
      return false;
    }
  }
}
