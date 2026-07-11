import '../entities/booking.dart';
import '../repositories/booking_repository.dart';

class GetMyBookings {
  final BookingRepository repository;

  GetMyBookings(this.repository);

  Future<List<Booking>> call() {
    return repository.getMyBookings();
  }
}