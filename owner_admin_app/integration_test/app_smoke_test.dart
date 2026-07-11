import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:owner_admin_app/main.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('app boots to router shell', (tester) async {
    await tester.pumpWidget(const StayLuxAdminApp());
    await tester.pumpAndSettle();
    expect(find.byType(StayLuxAdminApp), findsOneWidget);
  });
}
