class Booking {
  final int id;
  final int propertyId;
  final String propertyName;
  final int unitId;
  final String unitCode;
  final String checkIn;
  final String checkOut;
  final int guestCount;
  final String status;
  final String currency;
  final double totalAmount;
  final String createdAt;

  Booking({
    required this.id,
    required this.propertyId,
    required this.propertyName,
    required this.unitId,
    required this.unitCode,
    required this.checkIn,
    required this.checkOut,
    required this.guestCount,
    required this.status,
    required this.currency,
    required this.totalAmount,
    required this.createdAt,
  });
}

class BookingQuote {
  final int unitId;
  final int propertyId;
  final String propertyName;
  final String unitCode;
  final String checkIn;
  final String checkOut;
  final int nights;
  final int guestCount;
  final String bookingType;
  final String rentCycle;
  final double nightlyPrice;
  final double monthlyPrice;
  final double subtotal;
  final double discountAmount;
  final String discountLabel;
  final String couponCode;
  final double taxes;
  final double fees;
  final double total;
  final String currency;

  BookingQuote({
    required this.unitId,
    required this.propertyId,
    required this.propertyName,
    required this.unitCode,
    required this.checkIn,
    required this.checkOut,
    required this.nights,
    required this.guestCount,
    required this.bookingType,
    required this.rentCycle,
    required this.nightlyPrice,
    required this.monthlyPrice,
    required this.subtotal,
    this.discountAmount = 0,
    this.discountLabel = "",
    this.couponCode = "",
    required this.taxes,
    required this.fees,
    required this.total,
    required this.currency,
  });
}

class PaymentIntent {
  final int id;
  final int? bookingId;
  final String provider;
  final String providerReference;
  final String currency;
  final double amount;
  final String status;
  final String paymentMethod;
  final String clientSecret;
  final String verificationStatus;
  final int riskScore;
  final bool requiresManualReview;
  final String createdAt;

  PaymentIntent({
    required this.id,
    required this.bookingId,
    required this.provider,
    required this.providerReference,
    required this.currency,
    required this.amount,
    required this.status,
    required this.paymentMethod,
    required this.clientSecret,
    required this.verificationStatus,
    required this.riskScore,
    required this.requiresManualReview,
    required this.createdAt,
  });
}
