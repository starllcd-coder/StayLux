import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

import '../../../../core/network/api_client.dart';
import '../../data/datasources/booking_api.dart';
import '../../data/repositories/booking_repository_impl.dart';
import '../../domain/entities/booking.dart';
import '../../domain/usecases/cancel_booking.dart';
import '../../domain/usecases/create_booking.dart';
import '../../domain/usecases/get_my_bookings.dart';

class BookingState {
  final bool isLoading;
  final bool isSubmitting;
  final List<Booking> bookings;
  final BookingQuote? quote;
  final Booking? latestBooking;
  final PaymentIntent? latestPayment;
  final String? error;

  const BookingState({
    this.isLoading = false,
    this.isSubmitting = false,
    this.bookings = const [],
    this.quote,
    this.latestBooking,
    this.latestPayment,
    this.error,
  });

  BookingState copyWith({
    bool? isLoading,
    bool? isSubmitting,
    List<Booking>? bookings,
    BookingQuote? quote,
    Booking? latestBooking,
    PaymentIntent? latestPayment,
    String? error,
    bool clearError = false,
    bool clearLatest = false,
    bool clearQuote = false,
  }) {
    return BookingState(
      isLoading: isLoading ?? this.isLoading,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      bookings: bookings ?? this.bookings,
      quote: clearQuote ? null : (quote ?? this.quote),
      latestBooking: clearLatest ? null : (latestBooking ?? this.latestBooking),
      latestPayment: clearLatest ? null : (latestPayment ?? this.latestPayment),
      error: clearError ? null : (error ?? this.error),
    );
  }
}

final bookingControllerProvider =
    StateNotifierProvider<BookingController, BookingState>((ref) {
  return BookingController();
});

class BookingController extends StateNotifier<BookingState> {
  BookingController() : super(const BookingState());

  final _repository = BookingRepositoryImpl(BookingApi(ApiClient()));

  Future<void> loadMyBookings() async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
    );

    try {
      final items = await GetMyBookings(_repository).call();
      state = state.copyWith(
        isLoading: false,
        bookings: items,
        clearError: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _friendlyErrorMessage(e),
      );
    }
  }

  Future<bool> loadQuote({
    required int unitId,
    required String checkIn,
    required String checkOut,
    required int guestCount,
    String couponCode = "",
  }) async {
    state = state.copyWith(
      isSubmitting: true,
      clearError: true,
    );

    try {
      final quote = await _repository.getBookingQuote(
        unitId: unitId,
        checkIn: checkIn,
        checkOut: checkOut,
        guestCount: guestCount,
        couponCode: couponCode,
      );

      state = state.copyWith(
        isSubmitting: false,
        quote: quote,
        clearError: true,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: _friendlyErrorMessage(e),
      );
      return false;
    }
  }

  Future<bool> createBooking({
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
  }) async {
    state = state.copyWith(
      isSubmitting: true,
      clearError: true,
      clearLatest: true,
    );

    try {
      final result = await CreateBooking(_repository).call(
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

      state = state.copyWith(
        isSubmitting: false,
        latestBooking: result.booking,
        latestPayment: result.payment,
        quote: result.quote,
        clearError: true,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: _friendlyErrorMessage(e),
      );
      return false;
    }
  }

  Future<bool> cancel(int bookingId) async {
    state = state.copyWith(
      isSubmitting: true,
      clearError: true,
    );

    try {
      await CancelBooking(_repository).call(bookingId);
      final items = await GetMyBookings(_repository).call();

      state = state.copyWith(
        isSubmitting: false,
        bookings: items,
        clearError: true,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: _friendlyErrorMessage(e),
      );
      return false;
    }
  }

  void clearLatest() {
    state = state.copyWith(
      clearLatest: true,
      clearQuote: true,
      clearError: true,
    );
  }

  String _friendlyErrorMessage(Object error) {
    if (error is DioException) {
      final status = error.response?.statusCode ?? 0;
      final data = error.response?.data;
      if (data is Map<String, dynamic> && data.isNotEmpty) {
        final firstKey = data.keys.first;
        final firstValue = data[firstKey];
        if (firstValue is List && firstValue.isNotEmpty) {
          return firstValue.first.toString();
        }
        if (firstValue is String && firstValue.trim().isNotEmpty) {
          return firstValue;
        }
        if (firstValue != null) {
          return firstValue.toString();
        }
      }
      if (status == 400) {
        return "Please check booking details and try again.";
      }
      if (status == 401) {
        return "Session expired. Please login again.";
      }
      if (status >= 500) {
        return "Server error while processing booking.";
      }
      if (error.type == DioExceptionType.connectionError) {
        return "Cannot connect to backend. Please ensure server is running.";
      }
      if ((error.message ?? "").trim().isNotEmpty) {
        return error.message!;
      }
    }
    return error.toString();
  }
}
