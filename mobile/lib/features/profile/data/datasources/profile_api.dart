import '../models/profile_model.dart';
import '../../../../core/network/api_client.dart';

class ProfileApi {
  final ApiClient client;

  ProfileApi(this.client);

  Future<CustomerProfileModel> getProfile() async {
    final response = await client.get("/profile/");
    return CustomerProfileModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<CustomerProfileModel> updateProfile({
    required String fullName,
    required String email,
    required String mobile,
    required String preferredLanguage,
    required String preferredCountry,
  }) async {
    await client.patch(
      "/auth/me/",
      {
        "full_name": fullName,
        "email": email,
        "mobile": mobile,
        "preferred_language": preferredLanguage,
        "preferred_country": preferredCountry,
      },
    );

    final refreshed = await client.get("/profile/");
    return CustomerProfileModel.fromJson(refreshed.data as Map<String, dynamic>);
  }

  Future<List<TravelerProfileModel>> getTravelers() async {
    final response = await client.get("/profile/travelers/");
    final List results = response.data as List;
    return results
        .map((item) => TravelerProfileModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<TravelerProfileModel> createTraveler({
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
    final response = await client.post(
      "/profile/travelers/",
      {
        "full_name": fullName,
        "phone": phone,
        "whatsapp": whatsapp,
        "email": email,
        "nationality": nationality,
        "id_type": idType,
        "id_number": idNumber,
        "id_expiry": idExpiry,
        "address": address,
        "notes": notes,
        "is_default": isDefault,
      },
    );

    return TravelerProfileModel.fromJson(
      response.data["traveler"] as Map<String, dynamic>,
    );
  }

  Future<void> deleteTraveler(int travelerId) async {
    await client.delete("/profile/travelers/$travelerId/");
  }
}