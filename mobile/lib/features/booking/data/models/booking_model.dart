import '../../domain/entities/booking.dart';

class BookingModel extends Booking {
  BookingModel({
    required super.id,
    required super.propertyId,
    required super.propertyName,
    required super.unitId,
    required super.unitCode,
    required super.checkIn,
    required super.checkOut,
    required super.guestCount,
    required super.status,
    required super.currency,
    required super.totalAmount,
    required super.createdAt,
  });

  factory BookingModel.fromJson(Map<String, dynamic> json) {
    return BookingModel(
      id: json["id"] ?? 0,
      propertyId: json["property_id"] ?? 0,
      propertyName: (json["property_name"] ?? "").toString(),
      unitId: json["unit_id"] ?? 0,
      unitCode: (json["unit_code"] ?? "").toString(),
      checkIn: (json["check_in"] ?? "").toString(),
      checkOut: (json["check_out"] ?? "").toString(),
      guestCount: json["guest_count"] ?? 0,
      status: (json["status"] ?? "").toString(),
      currency: (json["currency"] ?? "GCC").toString(),
      totalAmount: _toDouble(json["total_amount"]),
      createdAt: (json["created_at"] ?? "").toString(),
    );
  }

  static double _toDouble(dynamic value) {
    if (value == null) return 0;
    return double.tryParse(value.toString()) ?? 0;
  }
}

class BookingQuoteModel extends BookingQuote {
  BookingQuoteModel({
    required super.unitId,
    required super.propertyId,
    required super.propertyName,
    required super.unitCode,
    required super.checkIn,
    required super.checkOut,
    required super.nights,
    required super.guestCount,
    required super.bookingType,
    required super.rentCycle,
    required super.nightlyPrice,
    required super.monthlyPrice,
    required super.subtotal,
    required super.discountAmount,
    required super.discountLabel,
    required super.couponCode,
    required super.taxes,
    required super.fees,
    required super.total,
    required super.currency,
  });

  factory BookingQuoteModel.fromJson(Map<String, dynamic> json) {
    return BookingQuoteModel(
      unitId: json["unit_id"] ?? 0,
      propertyId: json["property_id"] ?? 0,
      propertyName: (json["property_name"] ?? "").toString(),
      unitCode: (json["unit_code"] ?? "").toString(),
      checkIn: (json["check_in"] ?? "").toString(),
      checkOut: (json["check_out"] ?? "").toString(),
      nights: json["nights"] ?? 0,
      guestCount: json["guest_count"] ?? 0,
      bookingType: (json["booking_type"] ?? "").toString(),
      rentCycle: (json["rent_cycle"] ?? "").toString(),
      nightlyPrice: _toDouble(json["nightly_price"]),
      monthlyPrice: _toDouble(json["monthly_price"]),
      subtotal: _toDouble(json["subtotal"]),
      discountAmount: _toDouble(json["discount_amount"]),
      discountLabel: (json["discount_label"] ?? "").toString(),
      couponCode: (json["coupon_code"] ?? "").toString(),
      taxes: _toDouble(json["taxes"]),
      fees: _toDouble(json["fees"]),
      total: _toDouble(json["total"]),
      currency: (json["currency"] ?? "GCC").toString(),
    );
  }

  static double _toDouble(dynamic value) {
    if (value == null) return 0;
    return double.tryParse(value.toString()) ?? 0;
  }
}
