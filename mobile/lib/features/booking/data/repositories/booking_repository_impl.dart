import '../../domain/entities/booking.dart';
import '../../domain/repositories/booking_repository.dart';
import '../datasources/booking_api.dart';

class BookingRepositoryImpl implements BookingRepository {
  final BookingApi api;

  BookingRepositoryImpl(this.api);

  @override
  Future<BookingQuote> getBookingQuote({
    required int unitId,
    required String checkIn,
    required String checkOut,
    required int guestCount,
    String couponCode = "",
  }) {
    return api.getBookingQuote(
      unitId: unitId,
      checkIn: checkIn,
      checkOut: checkOut,
      guestCount: guestCount,
      couponCode: couponCode,
    );
  }

  @override
  Future<({Booking booking, BookingQuote quote, PaymentIntent payment})> createBooking({
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
    return api.createBooking(
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

  @override
  Future<List<Booking>> getMyBookings() {
    return api.getMyBookings();
  }

  @override
  Future<Booking> cancelBooking(int bookingId) {
    return api.cancelBooking(bookingId);
  }
}
