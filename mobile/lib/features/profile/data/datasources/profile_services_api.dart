import '../../../../core/network/api_client.dart';

class ProfileServicesApi {
  final ApiClient client;

  ProfileServicesApi(this.client);

  Future<List<Map<String, dynamic>>> getConversations() async {
    final response = await client.get("/chat/conversations/");
    return _asMapList(response.data);
  }

  Future<Map<String, dynamic>> createConversation({String title = ""}) async {
    final response = await client.post("/chat/conversations/", {"title": title});
    return _asMap(response.data);
  }

  Future<List<Map<String, dynamic>>> getMessages(int conversationId) async {
    final response = await client.get("/chat/conversations/$conversationId/messages/");
    return _asMapList(response.data);
  }

  Future<Map<String, dynamic>> sendMessage(int conversationId, String body, {String attachmentUrl = ""}) async {
    final response = await client.post(
      "/chat/conversations/$conversationId/messages/",
      {
        "body": body,
        "attachment_url": attachmentUrl,
      },
    );
    return _asMap(response.data);
  }

  Future<List<String>> getChatTemplates() async {
    final response = await client.get("/chat/templates/");
    final data = response.data;
    if (data is Map<String, dynamic>) {
      final raw = data["results"];
      if (raw is List) {
        return raw.map((e) => e.toString()).where((e) => e.trim().isNotEmpty).toList();
      }
    }
    return const [];
  }

  Future<List<Map<String, dynamic>>> getConciergeServices() async {
    final response = await client.get("/concierge/services/");
    return _asMapList(response.data);
  }

  Future<List<Map<String, dynamic>>> getConciergeRequests() async {
    final response = await client.get("/concierge/requests/");
    return _asMapList(response.data);
  }

  Future<Map<String, dynamic>> createConciergeRequest({
    required int serviceId,
    String requestedForDate = "",
    String notes = "",
  }) async {
    final payload = <String, dynamic>{"service": serviceId, "notes": notes};
    if (requestedForDate.trim().isNotEmpty) {
      payload["requested_for_date"] = requestedForDate;
    }
    final response = await client.post("/concierge/requests/", payload);
    return _asMap(response.data);
  }

  Future<List<Map<String, dynamic>>> getMembershipPlans() async {
    final response = await client.get("/growth/plans/");
    return _asMapList(response.data);
  }

  Future<List<Map<String, dynamic>>> getMemberships() async {
    final response = await client.get("/growth/membership/");
    return _asMapList(response.data);
  }

  Future<Map<String, dynamic>> subscribePlan(int planId) async {
    final response = await client.post("/growth/membership/", {"plan_id": planId});
    return _asMap(response.data);
  }

  Future<List<Map<String, dynamic>>> getReferrals() async {
    final response = await client.get("/growth/referrals/");
    return _asMapList(response.data);
  }

  Future<Map<String, dynamic>> createReferral(String email) async {
    final response = await client.post("/growth/referrals/", {"email": email});
    return _asMap(response.data);
  }

  Future<Map<String, dynamic>> requestVerification({
    required String purpose,
    String channel = "email",
  }) async {
    final response = await client.post(
      "/auth/verification/request/",
      {
        "purpose": purpose,
        "channel": channel,
      },
    );
    return _asMap(response.data);
  }

  Future<Map<String, dynamic>> verifyCode({
    required String purpose,
    required String code,
  }) async {
    final response = await client.post(
      "/auth/verification/check/",
      {
        "purpose": purpose,
        "code": code,
      },
    );
    return _asMap(response.data);
  }

  Future<List<Map<String, dynamic>>> getPaymentMethods() async {
    final response = await client.get("/profile/payment-methods/");
    return _asMapList(response.data);
  }

  Future<Map<String, dynamic>> addPaymentMethod({
    required String brand,
    required String last4,
    required int expMonth,
    required int expYear,
    bool isDefault = false,
    String providerToken = "",
  }) async {
    final response = await client.post(
      "/profile/payment-methods/",
      {
        "brand": brand,
        "last4": last4,
        "exp_month": expMonth,
        "exp_year": expYear,
        "provider_token": providerToken,
        "is_default": isDefault,
      },
    );
    return _asMap(response.data);
  }

  Future<void> removePaymentMethod(int id) async {
    await client.delete("/profile/payment-methods/$id/");
  }

  Future<Map<String, dynamic>> setDefaultPaymentMethod(int id) async {
    final response = await client.post("/profile/payment-methods/$id/default/", {});
    return _asMap(response.data);
  }

  Future<Map<String, dynamic>> getNotificationSettings() async {
    final response = await client.get("/profile/notification-settings/");
    return _asMap(response.data);
  }

  Future<Map<String, dynamic>> updateNotificationSettings({
    bool? marketingOptIn,
    bool? emailEnabled,
    bool? pushEnabled,
    bool? smsEnabled,
  }) async {
    final payload = <String, dynamic>{};
    if (marketingOptIn != null) payload["marketing_opt_in"] = marketingOptIn;
    if (emailEnabled != null) payload["email_notifications_enabled"] = emailEnabled;
    if (pushEnabled != null) payload["push_notifications_enabled"] = pushEnabled;
    if (smsEnabled != null) payload["sms_notifications_enabled"] = smsEnabled;
    final response = await client.patch("/profile/notification-settings/", payload);
    return _asMap(response.data);
  }

  List<Map<String, dynamic>> _asMapList(dynamic data) {
    if (data is List) {
      return data.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    if (data is Map<String, dynamic>) {
      final raw = data["results"];
      if (raw is List) {
        return raw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
      }
    }
    return const [];
  }

  Map<String, dynamic> _asMap(dynamic data) {
    if (data is Map<String, dynamic>) {
      return data;
    }
    return const {};
  }
}
