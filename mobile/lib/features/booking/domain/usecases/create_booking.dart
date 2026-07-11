import '../entities/booking.dart';
import '../repositories/booking_repository.dart';

class CreateBooking {
  final BookingRepository repository;

  CreateBooking(this.repository);

  Future<({Booking booking, BookingQuote quote, PaymentIntent payment})> call({
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
  }) {
    return repository.createBooking(
      unitId: unitId,
      checkIn: checkIn,
      checkOut: checkOut,
      guestCount: guestCount,
      travelerName: travelerName,
      travelerEmail: travelerEmail,
      travelerPhone: travelerPhone,
      notes: notes,
      paymentMethod: paymentMethod,
      paymentProvider: paymentProvider,
      paymentOption: paymentOption,
      couponCode: couponCode,
    );
  }
}
