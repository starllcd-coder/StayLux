import '../../../../core/network/api_client.dart';
import '../models/booking_model.dart';
import '../models/payment_model.dart';

class BookingApi {
  final ApiClient client;

  BookingApi(this.client);

  Future<BookingQuoteModel> getBookingQuote({
    required int unitId,
    required String checkIn,
    required String checkOut,
    required int guestCount,
    String couponCode = "",
  }) async {
    final response = await client.post(
      "/bookings/quote/",
      {
        "unit_id": unitId,
        "check_in": checkIn,
        "check_out": checkOut,
        "guest_count": guestCount,
        "coupon_code": couponCode,
      },
    );

    return BookingQuoteModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<
      ({
        BookingModel booking,
        BookingQuoteModel quote,
        PaymentIntentModel payment
      })> createBooking({
    required int unitId,
    required String checkIn,
    required String checkOut,
    required int guestCount,
    required String travelerName,
    required String travelerEmail,
    required String travelerPhone,
    required String notes,
    required String paymentMethod,
    required String paymentProvider,
    required String paymentOption,
    String couponCode = "",
  }) async {
    final response = await client.post(
      "/bookings/create/",
      {
        "unit_id": unitId,
        "check_in": checkIn,
        "check_out": checkOut,
        "guest_count": guestCount,
        "traveler_name": travelerName,
        "traveler_email": travelerEmail,
        "traveler_phone": travelerPhone,
        "notes": notes,
        "payment_method": paymentMethod,
        "payment_provider": paymentProvider,
        "payment_option": paymentOption,
        "coupon_code": couponCode,
      },
    );

    final data = response.data as Map<String, dynamic>;

    return (
      booking: BookingModel.fromJson(data["booking"] as Map<String, dynamic>),
      quote: BookingQuoteModel.fromJson(data["quote"] as Map<String, dynamic>),
      payment:
          PaymentIntentModel.fromJson(data["payment"] as Map<String, dynamic>),
    );
  }

  Future<List<BookingModel>> getMyBookings() async {
    final response = await client.get("/bookings/my/");
    final data = response.data;

    final List results;
    if (data is Map<String, dynamic>) {
      results = (data["results"] ?? []) as List;
    } else if (data is List) {
      results = data;
    } else {
      results = [];
    }

    return results
        .map((item) => BookingModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<BookingModel> cancelBooking(int bookingId) async {
    final response = await client.post("/bookings/$bookingId/cancel/", {});
    return BookingModel.fromJson(
      response.data["booking"] as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> verifyPayment({
    required int paymentId,
    String otpCode = "",
    String billingCountry = "",
  }) async {
    final payload = <String, dynamic>{
      "otp_code": otpCode,
    };
    if (billingCountry.trim().isNotEmpty) {
      payload["billing_country"] = billingCountry.trim();
    }
    final response = await client.post(
      "/bookings/payments/$paymentId/verify/",
      payload,
    );
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    return const {};
  }
}
