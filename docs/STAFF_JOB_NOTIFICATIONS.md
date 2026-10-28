# Staff job notifications

Housekeeping and maintenance assignments create a private notification for the
assigned active staff member. This works for assignments saved through the web
app, Django admin, or the API. Re-saving an unchanged assignment does not send
another notification. Reassigning sends a notification to the new assignee.
Unassigned jobs do not notify everyone in a department.

The owner/admin Flutter app checks the recipient's inbox every 20 seconds while
in the foreground and refreshes when resumed. Its unread banner opens the job
inbox. Tapping an item marks it read and opens the relevant jobs page. No job
details or read state are shared between recipients.

## Release

1. Deploy the updated backend and run `python manage.py migrate`.
2. Rebuild and install the updated `owner_admin_app` with
   `--dart-define=STAYLUX_API_BASE_URL=https://staylux-web.onrender.com`.
3. Log in as a housekeeping or maintenance staff member, assign a new matching
   job to that account, and verify its banner and inbox within 20 seconds.

The notification table records assignments made after this migration. Existing
assignments are not automatically replayed.

## Background / closed-app delivery

Optional Firebase Messaging support, device registration, and a server-side
sender are implemented and disabled by default. No Firebase project is currently
configured. Follow [Firebase setup](FIREBASE_PUSH_SETUP.md) to enable Android/iOS
closed-app notifications when the project and Apple push credentials are ready.
