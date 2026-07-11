import 'package:flutter_test/flutter_test.dart';
import 'package:owner_admin_app/data/datasources/admin_api.dart';
import 'package:owner_admin_app/data/datasources/api_client.dart';

class _FakeApiClient extends ApiClient {
  @override
  Future<Map<String, dynamic>> getMap(
    String path, {
    bool authenticated = true,
    String? bearerToken,
    Map<String, String>? queryParameters,
  }) async {
    if (path == '/api/reports/occupancy/') {
      return {
        'total_units': 15,
        'total_unit_nights': 300,
        'booked_nights': 210,
        'occupancy_percent': 70.0,
        'active_bookings_count': 12,
      };
    }

    if (path == '/api/reports/revenue/') {
      return {
        'invoices': {
          'revenue_total': '12500.500',
          'tax_total': '625.025',
          'outstanding_total': '1000.000',
        },
        'payments': {
          'collections_total': '11500.500',
        },
      };
    }

    if (path == '/api/reports/aging/') {
      return {
        'total_outstanding': '1000.000',
        'buckets': [
          {'label': '0-30', 'count': 2, 'amount': '600.000'},
          {'label': '31-60', 'count': 1, 'amount': '400.000'},
        ],
      };
    }

    if (path == '/api/reports/dashboard/') {
      return {
        'occupancy': {'occupancy_percent': 82.5},
        'units': {'occupied': 9},
        'maintenance': {'open': 3, 'in_progress': 2, 'total_requests': 5},
        'housekeeping': {'pending': 4, 'in_progress': 1, 'total_tasks': 7},
        'billing': {'revenue_total': '9999.000', 'collections_total': '8000.000'},
      };
    }

    return {};
  }

  @override
  Future<List<dynamic>> getList(
    String path, {
    bool authenticated = true,
    String? bearerToken,
    Map<String, String>? queryParameters,
  }) async {
    return [];
  }
}

void main() {
  final api = AdminApi(client: _FakeApiClient());

  test('parses occupancy report', () async {
    final model = await api.getOccupancyReport(
      propertyId: '1',
      period: 'monthly',
    );

    expect(model.totalUnits, 15);
    expect(model.bookedNights, 210);
    expect(model.occupancyPercent, 70.0);
    expect(model.activeBookingsCount, 12);
  });

  test('parses revenue report', () async {
    final model = await api.getRevenueReport(
      propertyId: '1',
      period: 'monthly',
    );

    expect(model.revenueTotal, '12500.500');
    expect(model.taxTotal, '625.025');
    expect(model.outstandingTotal, '1000.000');
    expect(model.collectionsTotal, '11500.500');
  });

  test('parses aging report', () async {
    final model = await api.getAgingReport(propertyId: '1');

    expect(model.totalOutstanding, '1000.000');
    expect(model.buckets.length, 2);
    expect(model.buckets.first.label, '0-30');
    expect(model.buckets.first.count, 2);
  });

  test('parses dashboard summary mapping', () async {
    final model = await api.getDashboard(propertyId: '1');

    expect(model.occupancy, 83);
    expect(model.activeGuests, 9);
    expect(model.openMaintenance, 5);
    expect(model.openHousekeeping, 5);
    expect(model.revenueToday, '9999.000');
  });
}
