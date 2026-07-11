import '../../domain/entities/booking.dart';

class PaymentIntentModel extends PaymentIntent {
  PaymentIntentModel({
    required super.id,
    required super.bookingId,
    required super.provider,
    required super.providerReference,
    required super.currency,
    required super.amount,
    required super.status,
    required super.paymentMethod,
    required super.clientSecret,
    required super.verificationStatus,
    required super.riskScore,
    required super.requiresManualReview,
    required super.createdAt,
  });

  factory PaymentIntentModel.fromJson(Map<String, dynamic> json) {
    return PaymentIntentModel(
      id: json["id"] ?? 0,
      bookingId: json["booking_id"],
      provider: (json["provider"] ?? "").toString(),
      providerReference: (json["provider_reference"] ?? "").toString(),
      currency: (json["currency"] ?? "GCC").toString(),
      amount: _toDouble(json["amount"]),
      status: (json["status"] ?? "").toString(),
      paymentMethod: (json["payment_method"] ?? "").toString(),
      clientSecret: (json["client_secret"] ?? "").toString(),
      verificationStatus: (json["verification_status"] ?? "pending").toString(),
      riskScore: _toInt(json["risk_score"]),
      requiresManualReview: json["requires_manual_review"] == true,
      createdAt: (json["created_at"] ?? "").toString(),
    );
  }

  static double _toDouble(dynamic value) {
    if (value == null) return 0;
    return double.tryParse(value.toString()) ?? 0;
  }

  static int _toInt(dynamic value) {
    if (value == null) return 0;
    return int.tryParse(value.toString()) ?? 0;
  }
}
