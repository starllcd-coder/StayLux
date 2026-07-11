import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:owner_admin_app/data/models/report_models.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_access_controller.dart';
import 'package:owner_admin_app/features/auth/controllers/admin_session_controller.dart';
import 'package:owner_admin_app/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:owner_admin_app/features/reports/presentation/pages/reports_page.dart';

class _FakeSession extends AdminSessionController {
  @override
  List<String> getPropertyIds() => ['1'];
}

class _FakeAccess extends AdminAccessController {
  _FakeAccess() : super(sessionController: _FakeSession());
}

class _FakeDashboard extends AdminDashboardController {
  @override
  Future<OccupancyReportModel> loadOccupancyReport({
    required String propertyId,
    required String period,
  }) async {
    return const OccupancyReportModel(
      totalUnits: 10,
      totalUnitNights: 100,
      bookedNights: 70,
      occupancyPercent: 70,
      activeBookingsCount: 6,
    );
  }

  @override
  Future<RevenueReportModel> loadRevenueReport({
    required String propertyId,
    required String period,
  }) async {
    return const RevenueReportModel(
      revenueTotal: '1000.000',
      taxTotal: '50.000',
      outstandingTotal: '100.000',
      collectionsTotal: '900.000',
    );
  }

  @override
  Future<AgingReportModel> loadAgingReport({
    required String propertyId,
  }) async {
    return const AgingReportModel(
      totalOutstanding: '100.000',
      buckets: [AgingBucketModel(label: '0-30', count: 1, amount: '100.000')],
    );
  }
}

void main() {
  testWidgets('ReportsPage renders report cards', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: ReportsPage(
          accessController: _FakeAccess(),
          sessionController: _FakeSession(),
          dashboardController: _FakeDashboard(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Occupancy'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Revenue'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Revenue'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Aging'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Aging'), findsOneWidget);
  });
}
