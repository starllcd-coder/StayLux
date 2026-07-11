import '../entities/booking.dart';

abstract class BookingRepository {
  Future<BookingQuote> getBookingQuote({
    required int unitId,
    required String checkIn,
    required String checkOut,
    required int guestCount,
    String couponCode = "",
  });

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
  });

  Future<List<Booking>> getMyBookings();

  Future<Booking> cancelBooking(int bookingId);
}
