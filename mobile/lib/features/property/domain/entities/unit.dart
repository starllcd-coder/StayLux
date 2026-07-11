class Unit {
  final int id;
  final String code;
  final String category;
  final String bedConfig;
  final int guestCapacity;
  final String status;
  final String currency;
  final double? nightlyPrice;
  final double? monthlyPrice;
  final double? estimatedTotal;

  Unit({
    required this.id,
    required this.code,
    required this.category,
    required this.bedConfig,
    required this.guestCapacity,
    required this.status,
    required this.currency,
    required this.nightlyPrice,
    required this.monthlyPrice,
    required this.estimatedTotal,
  });
}