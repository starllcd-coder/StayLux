# StayLux Mobile (Flutter)

Customer mobile app for StayLux (Flutter, iOS/Android).

## API Base URL

The app reads the API base URL from a compile-time define:

- `STAYLUX_API_BASE_URL`
- fallback: `http://127.0.0.1:8000/api/mobile`

Run example:

```bash
flutter run --dart-define=STAYLUX_API_BASE_URL=https://api.yourdomain.com/api/mobile
```

## Current Scope

- Auth: register, login, me, profile update
- Discovery: property list/search/details/units
- Booking: quote, create, my bookings, cancel
- Wishlist: list/toggle
- Reviews: list/create
- Notifications: list/mark-read
- Profile: traveler profiles CRUD

## Deferred Integrations

- Real payment gateway capture/confirmation
- Real OTP provider integration
- Real social token validation (Google/Apple SDK verification)
