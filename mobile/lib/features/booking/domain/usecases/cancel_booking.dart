import '../entities/booking.dart';
import '../repositories/booking_repository.dart';

class CancelBooking {
  final BookingRepository repository;

  CancelBooking(this.repository);

  Future<Booking> call(int bookingId) {
    return repository.cancelBooking(bookingId);
  }
}