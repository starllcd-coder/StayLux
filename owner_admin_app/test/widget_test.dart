import 'package:flutter_test/flutter_test.dart';
import 'package:owner_admin_app/main.dart';

void main() {
  testWidgets('App boots', (WidgetTester tester) async {
    await tester.pumpWidget(const StayLuxAdminApp());
    expect(find.byType(StayLuxAdminApp), findsOneWidget);
  });
}
