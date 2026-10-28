# Enable Firebase staff job push notifications later

The Firebase integration is implemented but OFF by default. It is independent
of the in-app job inbox. No Firebase account or credentials are needed to keep
using the app with push disabled. Firebase initialization failure also leaves
normal app functionality available.

## 1. Firebase project and platform registration

Create a Firebase project and register the Android and iOS apps using their
actual application IDs. The current Android application ID is
`com.example.owner_admin_app`; decide your final ID before releasing the app.
The iOS ID must match the Runner target's Bundle Identifier in Xcode.

With Flutter and Firebase CLI installed, run from `owner_admin_app`:

```text
flutter pub get
dart pub global activate flutterfire_cli
flutterfire configure --platforms=android,ios
```

Follow FlutterFire setup to install the platform files and Android Google
Services Gradle plugin. Keep the generated `google-services.json` and
`GoogleService-Info.plist` on your build machine. Those files must be available
when building an enabled app. Firebase requires Google Play services on Android.

For iOS, enable the Runner target's Push Notifications capability and Background
Modes > Remote notifications. Upload an APNs authentication key to Firebase's
Cloud Messaging settings. Signing entitlements are added when configuring the
Apple developer account; no placeholder Apple credentials are in this repo.

## 2. Mobile configuration and build

Copy `config/firebase.android.example.json` to `config/firebase.android.json`
(or the iOS equivalent). Fill the values using the matching platform's generated
`firebase_options.dart`: `apiKey`, `appId`, `messagingSenderId`, `projectId`, and
`iosBundleId` for iOS. Android and iOS use different app IDs/API keys.

Set `STAYLUX_FIREBASE_PUSH_ENABLED` to the string `true` in the copied file.
This app reads those values through `FirebasePushConfig`, not through an import
of the generated `firebase_options.dart` file. Never put a Firebase Admin
service-account private key in a mobile config file.

```text
flutter build apk --release --dart-define-from-file=config/firebase.android.json
flutter build ios --release --dart-define-from-file=config/firebase.ios.json
```

The iOS build requires macOS, Xcode, and valid signing. Run `flutter pub get`
before analysis or building to regenerate the dependency lockfile and platform
plugin registrants. Firebase dependency/platform compatibility and actual device
delivery still need validation on a Flutter-equipped build machine.

Staff are asked for phone notification permission after signing in. Registration
tokens refresh automatically. Logout disables the backend device and deletes its
FCM token. Push taps open the authenticated staff job inbox. Foreground messages
refresh the existing in-app banner rather than showing duplicate OS alerts.

## 3. Backend / Render

Deploy the updated Python requirements and run:

```text
python manage.py migrate
```

In Firebase Project settings > Service accounts, generate a Firebase Admin SDK
private key. Upload it as a Render secret file, for example
`/etc/secrets/firebase-service-account.json`. Configure:

```text
FIREBASE_PUSH_ENABLED=1
FIREBASE_SERVICE_ACCOUNT_FILE=/etc/secrets/firebase-service-account.json
```

Alternatively, use Application Default Credentials via
`GOOGLE_APPLICATION_CREDENTIALS` pointing to the secret file. The server and
mobile config must refer to the same Firebase project. Enable Firebase Cloud
Messaging API permissions for the server service account. Do not paste private
keys into GitHub, app code, logs, or chat.

Push sends after the job transaction commits. Failures never roll back the job
or its inbox notification. Expired/unregistered tokens are disabled. Successful
deliveries are recorded per notification/device. To retry failures or deliver
recent jobs after devices reconnect, schedule this command every minute on a
single worker (or run it manually):

```text
python manage.py send_staff_push
```

Retries consider unread jobs from the last 24 hours, skip finished/reassigned
jobs and inactive recipients/devices, and stop after five attempts per device.
Provider credentials and raw error messages are not stored in delivery logs.
FCM/APNs delivery is best effort; the durable in-app inbox remains authoritative.

## 4. Verify before release

1. Start with both switches OFF: login and in-app alerts must still work.
2. Enable both switches with real project configuration and install on a device.
3. Sign in as a housekeeping or maintenance employee and grant permission.
4. Assign a new job to that employee with the mobile app in the background.
5. Confirm the phone alert arrives; tap it and verify the private inbox opens.
6. Re-save the assignment and confirm no duplicate notification is created.
7. Log out and confirm future assignments do not reach the old device token.
8. Test token refresh, reassignment, closed-app launch, and both Android and iOS.

Phone lock-screen notifications intentionally contain no guest or unit details.
Force-stopping an app or disabling OS permissions can prevent push delivery.

Official references:
- https://firebase.google.com/docs/flutter/setup
- https://firebase.google.com/docs/cloud-messaging/flutter/get-started
- https://firebase.google.com/docs/cloud-messaging/flutter/receive-messages
