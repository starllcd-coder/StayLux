import 'package:firebase_core/firebase_core.dart';

/// Public mobile Firebase settings; server credentials never belong here.
class FirebasePushConfig {
  static const enabled = bool.fromEnvironment('STAYLUX_FIREBASE_PUSH_ENABLED', defaultValue: false);
  static const apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const appId = String.fromEnvironment('FIREBASE_APP_ID');
  static const senderId = String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
  static const projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  static const iosBundleId = String.fromEnvironment('FIREBASE_IOS_BUNDLE_ID');
  static bool get configured => [apiKey, appId, senderId, projectId].every((value) => value.isNotEmpty);
  static FirebaseOptions get options => FirebaseOptions(
    apiKey: apiKey, appId: appId, messagingSenderId: senderId, projectId: projectId,
    iosBundleId: iosBundleId.isEmpty ? null : iosBundleId,
  );
}
