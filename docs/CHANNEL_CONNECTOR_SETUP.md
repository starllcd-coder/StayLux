# Channel connector setup

Settings > Channel Integrations supports client-managed property IDs, room/rate
mapping, and encrypted API credentials for Agoda, Booking.com and Airbnb.

**No live platform adapter is implemented or approved yet.** Saving API details
and passing Check Setup do not authorize an account or sync reservations, rates,
availability or cancellations. Test Connection stays disabled. Platform access
must explicitly allow StayLux and the matching adapter must be implemented before
clients can establish real connections.

## Enable encrypted credential entry

Generate a Fernet key privately on an administrator's machine:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store the result as the `CHANNEL_CREDENTIALS_KEY` environment secret in Render
(and the local server's environment if needed), then restart the server. Use a
stable, backed-up key. Do not commit it to GitHub or paste it in chat. Changing
or losing the key makes existing credentials unreadable; they must then be
re-entered or recovered using the original key. Database backups alone cannot
recover encrypted credentials without this key.

Run `python manage.py migrate` when deploying. Without a valid key the API
credential inputs are hidden and credential submission is rejected. Non-secret
IDs and room mappings can still be saved.

## Client workflow

1. An Owner/Admin or Manager opens the selected property's Channel Integrations.
2. Enter the external hotel/property ID and map the platform's room/listing IDs.
3. Select the authentication method issued for the approved platform integration.
4. Fill only the API credential fields supplied by that platform. Website login
   passwords are not API credentials. OAuth may eventually require a separate
   platform authorization/consent step; saving a client ID/secret is not consent.
5. Save Setup. Blank credential fields preserve saved values; Remove saved
   credentials erases them. Saved values are never rendered back to the browser.
6. Check Setup validates local fields and encryption only. It does not make an
   external API request or confirm that credentials are valid.

Credentials are scoped to the selected property and platform and encrypted using
Fernet. Staff without property-management permission and individual apartment
owners cannot configure integrations. Transfer database exports containing
encrypted credentials privately and retain their encryption key separately.

The future connector layer must implement provider-specific authentication,
approval checks, token refresh, API validation, reservation deduplication,
availability/rate pushes, cancellation handling, webhooks/polling, and retries.
There are no user-supplied API endpoint URLs or executable connector uploads.
