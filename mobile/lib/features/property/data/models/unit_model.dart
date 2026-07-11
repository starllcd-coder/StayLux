import '../../domain/entities/unit.dart';

class UnitModel extends Unit {
  UnitModel({
    required super.id,
    required super.code,
    required super.category,
    required super.bedConfig,
    required super.guestCapacity,
    required super.status,
    required super.currency,
    required super.nightlyPrice,
    required super.monthlyPrice,
    required super.estimatedTotal,
  });

  factory UnitModel.fromJson(Map<String, dynamic> json) {
    final pricing = (json["pricing"] ?? {}) as Map<String, dynamic>;

    return UnitModel(
      id: _toInt(json["id"]),
      code: (json["code"] ?? "").toString(),
      category: (json["category"] ?? "").toString(),
      bedConfig: (json["bed_config"] ?? "").toString(),
      guestCapacity: _toInt(json["guest_capacity"]),
      status: (json["status"] ?? "").toString(),
      currency: (pricing["currency"] ?? "GCC").toString(),
      nightlyPrice: _toDouble(pricing["nightly_price"]),
      monthlyPrice: _toDouble(pricing["monthly_price"]),
      estimatedTotal: _toDouble(pricing["estimated_total"]),
    );
  }

  static int _toInt(dynamic value) {
    if (value == null) return 0;
    if (value is int) return value;
    return int.tryParse(value.toString()) ?? 0;
  }

  static double? _toDouble(dynamic value) {
    if (value == null) return null;
    return double.tryParse(value.toString());
  }
}
