import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_button.dart';
import '../controllers/booking_controller.dart';

class BookingPage extends ConsumerStatefulWidget {
  final int unitId;
  final String propertyName;
  final String unitCode;
  final String propertyCountry;

  const BookingPage({
    super.key,
    required this.unitId,
    required this.propertyName,
    required this.unitCode,
    this.propertyCountry = "",
  });

  @override
  ConsumerState<BookingPage> createState() => _BookingPageState();
}

class _BookingPageState extends ConsumerState<BookingPage> {
  final _formKey = GlobalKey<FormState>();
  Timer? _quoteDebounce;

  final checkInController = TextEditingController();
  final checkOutController = TextEditingController();
  final guestCountController = TextEditingController(text: "2");
  final travelerNameController = TextEditingController();
  final travelerEmailController = TextEditingController();
  final travelerPhoneController = TextEditingController();
  final couponCodeController = TextEditingController();
  final notesController = TextEditingController();

  String paymentOption = "pay_now";

  @override
  void initState() {
    super.initState();
    checkInController.addListener(_scheduleAutoQuote);
    checkOutController.addListener(_scheduleAutoQuote);
    guestCountController.addListener(_scheduleAutoQuote);
    couponCodeController.addListener(_scheduleAutoQuote);
  }

  @override
  void dispose() {
    _quoteDebounce?.cancel();
    checkInController.removeListener(_scheduleAutoQuote);
    checkOutController.removeListener(_scheduleAutoQuote);
    guestCountController.removeListener(_scheduleAutoQuote);
    couponCodeController.removeListener(_scheduleAutoQuote);
    checkInController.dispose();
    checkOutController.dispose();
    guestCountController.dispose();
    travelerNameController.dispose();
    travelerEmailController.dispose();
    travelerPhoneController.dispose();
    couponCodeController.dispose();
    notesController.dispose();
    super.dispose();
  }

  Future<void> _pickDate(TextEditingController controller) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: DateTime(now.year + 2),
      initialDate: now,
    );

    if (picked != null) {
      controller.text =
          "${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}";
      _scheduleAutoQuote();
    }
  }

  String? _validateDates() {
    if (checkInController.text.trim().isEmpty ||
        checkOutController.text.trim().isEmpty) {
      return "Select check-in and check-out dates".tr(context);
    }

    final checkIn = DateTime.tryParse(checkInController.text.trim());
    final checkOut = DateTime.tryParse(checkOutController.text.trim());

    if (checkIn == null || checkOut == null) {
      return "Invalid date format".tr(context);
    }

    if (!checkOut.isAfter(checkIn)) {
      return "Check-out must be after check-in".tr(context);
    }

    return null;
  }

  Future<bool> _loadQuote({required bool showErrors}) async {
    final dateError = _validateDates();
    if (dateError != null) {
      if (showErrors) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(dateError)),
        );
      }
      return false;
    }

    final guests = int.tryParse(guestCountController.text.trim()) ?? 0;
    if (guests <= 0) {
      if (showErrors) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Enter valid guest count".tr(context))),
        );
      }
      return false;
    }

    final ok = await ref.read(bookingControllerProvider.notifier).loadQuote(
          unitId: widget.unitId,
          checkIn: checkInController.text.trim(),
          checkOut: checkOutController.text.trim(),
          guestCount: guests,
          couponCode: couponCodeController.text.trim(),
        );

    if (!mounted) return false;
    final state = ref.read(bookingControllerProvider);

    if (!ok && showErrors) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text((state.error ?? "Could not load quote".tr(context))),
        ),
      );
    }
    return ok;
  }

  void _scheduleAutoQuote() {
    _quoteDebounce?.cancel();
    _quoteDebounce = Timer(const Duration(milliseconds: 350), () async {
      if (!mounted) return;
      if (checkInController.text.trim().isEmpty ||
          checkOutController.text.trim().isEmpty) {
        return;
      }
      if (_validateDates() != null) return;
      if ((int.tryParse(guestCountController.text.trim()) ?? 0) <= 0) return;
      await _loadQuote(showErrors: false);
    });
  }

  Future<void> _createBooking() async {
    final paymentMethod =
        paymentOption == "pay_at_property" ? "pay_at_property" : "card";
    final paymentProvider =
        paymentOption == "pay_at_property" ? "property_frontdesk" : "pending_provider";

    final ok = await ref.read(bookingControllerProvider.notifier).createBooking(
          unitId: widget.unitId,
          checkIn: checkInController.text.trim(),
          checkOut: checkOutController.text.trim(),
          guestCount: int.tryParse(guestCountController.text.trim()) ?? 1,
          travelerName: travelerNameController.text.trim(),
          travelerEmail: travelerEmailController.text.trim(),
          travelerPhone: travelerPhoneController.text.trim(),
          notes: notesController.text.trim(),
          paymentMethod: paymentMethod,
          paymentProvider: paymentProvider,
          paymentOption: paymentOption,
          couponCode: couponCodeController.text.trim(),
        );

    if (!mounted) return;

    final state = ref.read(bookingControllerProvider);
    if (ok && state.latestBooking != null) {
      context.push(
        "/booking-success",
        extra: {
          "propertyName": state.latestBooking!.propertyName,
          "unitCode": state.latestBooking!.unitCode,
          "bookingId": state.latestBooking!.id,
          "paymentId": state.latestPayment?.id ?? 0,
          "total": state.quote?.total ?? 0.0,
          "currency": state.latestBooking!.currency,
          "paymentMethod": state.latestPayment?.paymentMethod ?? paymentMethod,
          "propertyCountry": widget.propertyCountry,
        },
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text((state.error ?? "Booking failed".tr(context)))),
    );
  }

  Future<void> _continueToPayment() async {
    if (!_formKey.currentState!.validate()) return;

    final dateError = _validateDates();
    if (dateError != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(dateError)),
      );
      return;
    }

    final hasQuote = ref.read(bookingControllerProvider).quote != null;
    if (!hasQuote) {
      final quoteOk = await _loadQuote(showErrors: true);
      if (!quoteOk) return;
    }
    await _createBooking();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(bookingControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          "Book Stay".tr(context),
          style: TextStyle(
            color: AppTheme.darkText,
            fontWeight: FontWeight.w700,
          ),
        ),
        backgroundColor: AppTheme.ivory,
      ),
      backgroundColor: AppTheme.ivory,
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF132B52), Color(0xFF244A82)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.propertyName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      "${"Unit".tr(context)} ${widget.unitCode}",
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              _StepTag(text: "Step 1: Select dates".tr(context)),
              const SizedBox(height: 10),
              _SectionCard(
                child: Column(
                  children: [
                    TextFormField(
                      controller: checkInController,
                      readOnly: true,
                      onTap: () => _pickDate(checkInController),
                      decoration: InputDecoration(
                        labelText: "Check-in".tr(context),
                        prefixIcon: Icon(Icons.calendar_month_outlined),
                      ),
                      validator: (value) =>
                          value == null || value.isEmpty
                              ? "Check-in is required".tr(context)
                              : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: checkOutController,
                      readOnly: true,
                      onTap: () => _pickDate(checkOutController),
                      decoration: InputDecoration(
                        labelText: "Check-out".tr(context),
                        prefixIcon: Icon(Icons.calendar_month_outlined),
                      ),
                      validator: (value) =>
                          value == null || value.isEmpty
                              ? "Check-out is required".tr(context)
                              : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: guestCountController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                        labelText: "Guests".tr(context),
                        prefixIcon: Icon(Icons.group_outlined),
                      ),
                      validator: (value) {
                        final count = int.tryParse(value ?? "");
                        if (count == null || count <= 0) {
                          return "Enter valid guest count".tr(context);
                        }
                        return null;
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              _StepTag(text: "Step 2: Traveler details".tr(context)),
              const SizedBox(height: 10),
              _SectionCard(
                child: Column(
                  children: [
                    TextFormField(
                      controller: travelerNameController,
                      decoration: InputDecoration(
                        labelText: "Traveler Name".tr(context),
                        prefixIcon: Icon(Icons.person_outline),
                      ),
                      validator: (value) =>
                          value == null || value.trim().isEmpty
                              ? "Traveler name is required".tr(context)
                              : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: travelerEmailController,
                      keyboardType: TextInputType.emailAddress,
                      decoration: InputDecoration(
                        labelText: "Traveler Email".tr(context),
                        prefixIcon: Icon(Icons.email_outlined),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return "Traveler email is required".tr(context);
                        }
                        if (!value.contains("@")) {
                          return "Enter valid email".tr(context);
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: travelerPhoneController,
                      keyboardType: TextInputType.phone,
                      decoration: InputDecoration(
                        labelText: "Traveler Phone".tr(context),
                        prefixIcon: Icon(Icons.phone_outlined),
                      ),
                      validator: (value) {
                        final raw = (value ?? "").trim();
                        if (raw.isEmpty) return null;
                        final digits = raw.replaceAll(RegExp(r"\D"), "");
                        if (digits.length < 7) {
                          return "Enter valid phone number".tr(context);
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: couponCodeController,
                      textCapitalization: TextCapitalization.characters,
                      decoration: InputDecoration(
                        labelText: "Coupon Code".tr(context),
                        prefixIcon: Icon(Icons.local_offer_outlined),
                        hintText: "WELCOME10",
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: notesController,
                      maxLines: 3,
                      decoration: InputDecoration(
                        labelText: "Notes".tr(context),
                        alignLabelWithHint: true,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              _StepTag(text: "Step 3: Payment option".tr(context)),
              const SizedBox(height: 10),
              _SectionCard(
                child: Column(
                  children: [
                    _PaymentOptionTile(
                      selected: paymentOption == "pay_now",
                      title: "Pay Now".tr(context),
                      subtitle: "Card payment security verification will be available."
                          .tr(context),
                      onTap: () => setState(() => paymentOption = "pay_now"),
                    ),
                    const Divider(height: 1),
                    _PaymentOptionTile(
                      selected: paymentOption == "pay_at_property",
                      title: "Pay at Property".tr(context),
                      subtitle: "Reserve now and pay at reception/front desk."
                          .tr(context),
                      onTap: () => setState(() => paymentOption = "pay_at_property"),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              AppButton(
                text: paymentOption == "pay_at_property"
                    ? "Confirm Reservation".tr(context)
                    : "Continue to Payment".tr(context),
                isLoading: state.isSubmitting,
                onPressed: _continueToPayment,
              ),
              if (state.quote != null) ...[
                const SizedBox(height: 18),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: const Color(0xFFE5DECF)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "Step 4: Confirm price and book".tr(context),
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.primaryNavy,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "Booking Summary".tr(context),
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.darkText,
                        ),
                      ),
                      const SizedBox(height: 12),
                      _SummaryRow("Nights".tr(context), "${state.quote!.nights}"),
                      _SummaryRow(
                        "Nightly Price".tr(context),
                        "${state.quote!.currency} ${state.quote!.nightlyPrice.toStringAsFixed(2)}",
                      ),
                      _SummaryRow(
                        "Subtotal".tr(context),
                        "${state.quote!.currency} ${state.quote!.subtotal.toStringAsFixed(2)}",
                      ),
                      if (state.quote!.discountAmount > 0)
                        _SummaryRow(
                          state.quote!.discountLabel.isEmpty
                              ? "Discount".tr(context)
                              : "${"Discount".tr(context)} (${state.quote!.discountLabel})",
                          "- ${state.quote!.currency} ${state.quote!.discountAmount.toStringAsFixed(2)}",
                        ),
                      _SummaryRow(
                        "Taxes".tr(context),
                        "${state.quote!.currency} ${state.quote!.taxes.toStringAsFixed(2)}",
                      ),
                      _SummaryRow(
                        "Fees".tr(context),
                        "${state.quote!.currency} ${state.quote!.fees.toStringAsFixed(2)}",
                      ),
                      const Divider(height: 24),
                      _SummaryRow(
                        "Total".tr(context),
                        "${state.quote!.currency} ${state.quote!.total.toStringAsFixed(2)}",
                        isBold: true,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "Taxes and fees are shown above with full transparency."
                            .tr(context),
                        style: TextStyle(color: AppTheme.mutedText, fontSize: 12),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        "Free cancellation up to 24 hours before check-in."
                            .tr(context),
                        style: TextStyle(color: AppTheme.mutedText, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final String value;
  final bool isBold;

  const _SummaryRow(
    this.label,
    this.value, {
    this.isBold = false,
  });

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
      color: AppTheme.darkText,
      fontWeight: isBold ? FontWeight.w800 : FontWeight.w500,
      fontSize: isBold ? 16 : 14,
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(child: Text(label, style: style)),
          Text(value, style: style),
        ],
      ),
    );
  }
}

class _StepTag extends StatelessWidget {
  final String text;

  const _StepTag({required this.text});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: const Color(0xFFF2E7CB),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFFE2D1A7)),
        ),
        child: Text(
          text,
          style: const TextStyle(
            color: AppTheme.primaryNavy,
            fontWeight: FontWeight.w700,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final Widget child;

  const _SectionCard({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.cardWhite,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE5DCCB)),
      ),
      child: child,
    );
  }
}

class _PaymentOptionTile extends StatelessWidget {
  final bool selected;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _PaymentOptionTile({
    required this.selected,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 2, right: 10),
              child: Icon(
                selected ? Icons.radio_button_checked : Icons.radio_button_off,
                color: selected ? AppTheme.primaryNavy : AppTheme.mutedText,
                size: 22,
              ),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      color: AppTheme.darkText,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      color: AppTheme.mutedText,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
