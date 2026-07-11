import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/utils/gcc_region.dart';
import '../../../../core/widgets/app_button.dart';
import '../../data/datasources/booking_api.dart';

class BookingSuccessPage extends StatefulWidget {
  final String propertyName;
  final String unitCode;
  final int bookingId;
  final int paymentId;
  final double total;
  final String currency;
  final String paymentMethod;
  final String propertyCountry;
  final String appCountry;

  const BookingSuccessPage({
    super.key,
    required this.propertyName,
    required this.unitCode,
    required this.bookingId,
    required this.paymentId,
    required this.total,
    required this.currency,
    this.paymentMethod = "",
    this.propertyCountry = "",
    this.appCountry = "",
  });

  @override
  State<BookingSuccessPage> createState() => _BookingSuccessPageState();
}

class _BookingSuccessPageState extends State<BookingSuccessPage> {
  bool verifying = false;
  String verificationText = "Pending confirmation";
  final bookingApi = BookingApi(ApiClient());

  Future<void> _verifyPayment() async {
    if (widget.paymentId <= 0) return;
    setState(() => verifying = true);
    try {
      final result = await bookingApi.verifyPayment(
        paymentId: widget.paymentId,
        otpCode: "123456",
        billingCountry: _billingCountryCode(),
      );
      final security = result["security"];
      final status = (security is Map<String, dynamic>)
          ? (security["verification_status"] ?? "pending").toString()
          : "pending";
      setState(() {
        verificationText = status;
        verifying = false;
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("${"Verification".tr(context)}: $status"),
        ),
      );
    } catch (e) {
      setState(() => verifying = false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("${"Verification failed".tr(context)}: $e"),
        ),
      );
    }
  }

  String _billingCountryCode() {
    final byProperty = countryCodeForCountry(widget.propertyCountry);
    if (byProperty.isNotEmpty) return byProperty;
    final byApp = countryCodeForCountry(widget.appCountry);
    if (byApp.isNotEmpty) return byApp;
    return defaultBillingCountryCode();
  }

  bool get _isPayAtProperty => widget.paymentMethod == "pay_at_property";

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.ivory,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(22),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircleAvatar(
                radius: 42,
                backgroundColor: Color(0xFFE8F7EC),
                child: Icon(
                  Icons.check_circle_rounded,
                  color: Colors.green,
                  size: 54,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                "Booking Confirmed".tr(context),
                style: TextStyle(
                  color: AppTheme.darkText,
                  fontSize: 26,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                widget.propertyName,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppTheme.primaryNavy,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                "${"Unit".tr(context)} ${widget.unitCode}",
                style: const TextStyle(
                  color: AppTheme.mutedText,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Column(
                  children: [
                    _InfoRow("Booking ID".tr(context), "#${widget.bookingId}"),
                    const SizedBox(height: 12),
                  _InfoRow(
                    "Amount".tr(context),
                    "${widget.currency} ${widget.total.toStringAsFixed(2)}",
                  ),
                  const SizedBox(height: 12),
                    _InfoRow(
                      "Status".tr(context),
                      _isPayAtProperty
                          ? "Pay at property".tr(context)
                          : verificationText,
                    ),
                ],
              ),
              ),
              const SizedBox(height: 28),
              if (widget.paymentId > 0 && !_isPayAtProperty)
                AppButton(
                  text: verifying
                      ? "Verifying...".tr(context)
                      : "Verify Payment Security".tr(context),
                  onPressed: verifying ? null : _verifyPayment,
                ),
              if (widget.paymentId > 0 && !_isPayAtProperty) const SizedBox(height: 12),
              AppButton(
                text: "View My Bookings".tr(context),
                onPressed: () => context.go("/booking-history"),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => context.go("/home"),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.primaryNavy,
                  side: const BorderSide(color: AppTheme.primaryNavy),
                  minimumSize: const Size(double.infinity, 52),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                child: Text("Back to Home".tr(context)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            color: AppTheme.darkText,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
