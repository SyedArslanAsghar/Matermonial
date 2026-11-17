# Matermonial — API and Third-Party Integration Specifications

**Version:** 1.0  
**Date:** 11 November 2026  
**API base path:** `/api/v1/`

## 1. API principles

1. Use REST conventions and JSON responses.
2. Use UUIDs for major resource identifiers.
3. Require authentication for protected operations.
4. Enforce object-level permissions on every private resource.
5. Keep business logic in domain services.
6. Use pagination for collection endpoints.
7. Document endpoints with OpenAPI.
8. Use standardized errors.
9. Use idempotency keys for payment and retry-sensitive operations.
10. Never trust frontend authorization or payment-success claims.
11. Do not expose private database fields in serializers.
12. Keep API versioning independent from application release versions.

## 2. Authentication endpoints

Recommended endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register/` | Create account |
| POST | `/auth/otp/send/` | Send phone OTP |
| POST | `/auth/otp/verify/` | Verify OTP |
| POST | `/auth/login/` | Authenticate |
| POST | `/auth/logout/` | Revoke current session/token |
| POST | `/auth/token/refresh/` | Refresh access token, if using refresh-token architecture |
| POST | `/auth/password/forgot/` | Start password reset |
| POST | `/auth/password/reset/` | Complete password reset |
| GET | `/auth/me/` | Current account |
| GET | `/auth/sessions/` | List permitted session history |
| DELETE | `/auth/sessions/{id}/` | Revoke a session |

Use a secure token/session architecture. If JWT is selected, use short-lived access tokens, protected refresh-token handling, rotation, and revocation strategy. Store tokens securely on mobile.

## 3. Profile endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/profiles/` | Create own profile |
| GET | `/profiles/me/` | Retrieve own profile |
| PATCH | `/profiles/me/` | Update own profile |
| GET | `/profiles/{id}/` | View eligible profile |
| PATCH | `/profiles/{id}/` | Update represented profile if authorized |
| GET | `/profiles/{id}/completion/` | Profile completion |
| POST | `/profiles/{id}/submit-review/` | Submit profile for applicable review |
| POST | `/profiles/{id}/photos/` | Upload photo |
| GET | `/profiles/{id}/photos/` | List accessible photos |
| PATCH | `/profiles/{id}/photos/{photo_id}/` | Update permitted photo metadata |
| DELETE | `/profiles/{id}/photos/{photo_id}/` | Remove own/authorized photo |

A profile ID in the URL does not establish ownership or manager authorization.

## 4. Partner preference endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/profiles/me/partner-preferences/` | Retrieve preferences |
| PUT | `/profiles/me/partner-preferences/` | Replace preferences |
| PATCH | `/profiles/me/partner-preferences/` | Partially update preferences |

Validate age and earning ranges. Preserve nullable Boolean semantics.

## 5. Verification endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/verification/identity/` | Start identity verification |
| GET | `/verification/identity/me/` | Current verification status |
| POST | `/verification/identity/{id}/documents/` | Upload document |
| POST | `/verification/identity/{id}/resubmit/` | Resubmit after rejection |
| GET | `/verification/identity/{id}/history/` | Authorized verification history |

Administrative review endpoints should be separately permission-protected.

Do not expose internal reviewer notes or duplicate-document fingerprints through user APIs.

## 6. Family management endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/family-management/authorizations/` | List relevant authorizations |
| POST | `/family-management/authorizations/` | Invite manager |
| POST | `/family-management/authorizations/{id}/accept/` | Accept invitation |
| POST | `/family-management/authorizations/{id}/reject/` | Reject invitation |
| POST | `/family-management/authorizations/{id}/pause/` | Pause |
| POST | `/family-management/authorizations/{id}/resume/` | Resume |
| POST | `/family-management/authorizations/{id}/revoke/` | Revoke |
| GET | `/family-management/permissions/` | List permission catalog |
| GET | `/family-management/permission-groups/` | List templates |
| PUT | `/family-management/authorizations/{id}/permissions/` | Update permissions |
| GET | `/family-management/authorizations/{id}/history/` | Authorization history |
| GET | `/family-management/profile-access-history/` | Owner's profile-access history |

The owner must be the only actor allowed to manage authorization by default.

## 7. Search and matching endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/search/profiles/` | Search eligible profiles |
| GET | `/matching/recommendations/` | Rule-based recommendations |
| POST | `/search/saved/` | Save named search |
| GET | `/search/saved/` | List saved searches |
| PATCH | `/search/saved/{id}/` | Update saved search |
| DELETE | `/search/saved/{id}/` | Delete saved search |
| GET | `/favorites/` | List favorites |
| POST | `/favorites/` | Add favorite |
| PATCH | `/favorites/{id}/` | Update private note |
| DELETE | `/favorites/{id}/` | Remove favorite |

Search must exclude ineligible, blocked, and hidden profiles before returning results.

## 8. Interest and request endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/interests/` | Express interest |
| GET | `/interests/received/` | Received interests |
| GET | `/interests/sent/` | Sent interests |
| POST | `/interests/{id}/show-interest-back/` | Show interest back |
| POST | `/interests/{id}/formal-request/` | Convert/advance to formal request according to business rules |
| POST | `/interests/{id}/decline/` | Decline interest |
| POST | `/requests/` | Create formal request |
| GET | `/requests/` | List relevant requests |
| GET | `/requests/{id}/` | Retrieve authorized request |
| POST | `/requests/{id}/accept/` | Accept |
| POST | `/requests/{id}/decline/` | Decline |
| POST | `/requests/{id}/withdraw/` | Withdraw |
| GET | `/requests/{id}/history/` | Request history |

The exact relationship between a lightweight interest record and a formal request must be implemented consistently with the approved interest workflow. Do not create duplicate records or charge a formal-request credit for an action that is only an interest unless the configured business rule explicitly requires it.

## 9. Connection endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/connections/` | List connections |
| GET | `/connections/{id}/` | Connection detail |
| POST | `/connections/{id}/pause/` | Pause |
| POST | `/connections/{id}/resume/` | Resume |
| POST | `/connections/{id}/close/` | Close |
| POST | `/connections/{id}/complete/` | Mark completed/engaged |
| POST | `/connections/{id}/reopen/` | Request mutual reopening |
| GET | `/connections/{id}/history/` | Connection history |
| GET | `/connections/{id}/progress/` | Relationship progress |
| PATCH | `/connections/{id}/progress/` | Update progress |
| GET | `/connections/{id}/progress/history/` | Progress history |

Enforce connection state and block restrictions on every action.

## 10. Messaging endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/conversations/` | List conversations |
| GET | `/conversations/{id}/` | Conversation detail |
| GET | `/conversations/{id}/messages/` | Paginated message history |
| POST | `/conversations/{id}/messages/` | Send message |
| POST | `/conversations/{id}/attachments/` | Upload attachment |
| POST | `/messages/{id}/read/` | Mark read |
| GET | `/documents/` | List own/accessible documents |
| POST | `/documents/` | Upload shared document |
| POST | `/documents/{id}/share/` | Grant access |
| POST | `/documents/{id}/revoke-access/` | Revoke access |
| GET | `/documents/{id}/access-history/` | Authorized access history |

Message sending requires an active connection and valid participant authorization.

## 11. Privacy endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/privacy/settings/` | Retrieve privacy settings |
| PATCH | `/privacy/settings/` | Update privacy settings |
| GET | `/privacy/blocked-profiles/` | List blocked profiles |
| POST | `/privacy/blocked-profiles/` | Block profile |
| DELETE | `/privacy/blocked-profiles/{id}/` | Unblock |
| GET | `/privacy/hidden-profiles/` | List hidden profiles |
| POST | `/privacy/hidden-profiles/` | Hide profile |
| DELETE | `/privacy/hidden-profiles/{id}/` | Unhide |
| POST | `/privacy/photo-access-requests/` | Request photo access |
| POST | `/privacy/photo-access-requests/{id}/approve/` | Approve |
| POST | `/privacy/photo-access-requests/{id}/decline/` | Decline |
| GET | `/privacy/visitor-history/` | Retrieve eligible visitor history |
| DELETE | `/privacy/visitor-history/{id}/` | Remove visible visitor record |

Do not reveal the existence of a hidden or blocked relationship through error messages.

## 12. Subscription, credit, and payment endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/subscriptions/plans/` | List active plans |
| GET | `/subscriptions/me/` | Current subscription |
| POST | `/subscriptions/purchase/` | Initiate subscription purchase |
| POST | `/subscriptions/cancel/` | Cancel future renewal |
| GET | `/credits/wallet/` | Current credit balances |
| GET | `/credits/transactions/` | Transaction history |
| GET | `/credits/packages/` | Active top-up packages |
| POST | `/credits/purchase/` | Initiate top-up purchase |
| GET | `/payments/{id}/` | Retrieve own payment |
| POST | `/payments/jazzcash/callback/` | Gateway callback endpoint |

The callback endpoint must be verified according to the gateway contract. It must not accept a frontend assertion of payment success.

Payment endpoints should use idempotency and merchant-reference validation.

## 13. Notification endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/notifications/` | List notifications |
| POST | `/notifications/{id}/read/` | Mark read |
| POST | `/notifications/read-all/` | Mark all read |
| GET | `/notifications/preferences/` | Retrieve preferences |
| PATCH | `/notifications/preferences/` | Update preferences |
| GET | `/notifications/devices/` | List push devices |
| POST | `/notifications/devices/` | Register push device |
| DELETE | `/notifications/devices/{id}/` | Revoke push device |

## 14. Moderation endpoints

User-facing:

- `POST /reports/`
- `GET /reports/my/`
- `GET /reports/{id}/`
- `POST /moderation/appeals/`
- `GET /moderation/appeals/my/`

Administrative moderation endpoints must be placed under an admin namespace or otherwise clearly separated and permission-protected.

Do not expose other users' reports or internal evidence to ordinary users.

## 15. Data export and account deletion endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/data-exports/` | Request export |
| GET | `/data-exports/` | List own export requests |
| GET | `/data-exports/{id}/` | Export status |
| POST | `/data-exports/{id}/verify/` | Complete required identity confirmation |
| GET | `/data-exports/{id}/download/` | Obtain temporary download access |
| POST | `/account-deletion/` | Request account deletion |
| GET | `/account-deletion/` | Retrieve own deletion request |
| POST | `/account-deletion/{id}/cancel/` | Cancel during recovery period |

The export must include only data the requester is authorized to access.

## 16. API pagination

Use a consistent pagination response.

Recommended format:

```json
{
  "count": 100,
  "next": "https://example.com/api/v1/profiles/?page=2",
  "previous": null,
  "results": []
}
```

Set sensible default and maximum page sizes through backend settings.

## 17. Third-party integration architecture

Define provider interfaces instead of placing provider-specific code throughout business modules.

Recommended interfaces:

```text
PaymentProvider
├── initiate_payment()
├── verify_callback()
├── query_transaction()
└── process_refund()

SMSProvider
├── send_message()
└── get_delivery_status()

EmailProvider
├── send_email()
└── get_delivery_status()

PushProvider
├── send_notification()
└── invalidate_token()

StorageProvider
├── upload()
├── delete()
├── generate_temporary_url()
└── inspect_metadata()

OTPProvider
├── generate()
├── dispatch()
└── verify()
```

Implement local/mock providers for development and test environments.

## 18. JazzCash integration

The payment module must:

1. Create a local pending payment transaction.
2. Generate a unique merchant reference.
3. Initiate payment through the configured provider.
4. Redirect or otherwise guide the user through the provider's approved payment flow.
5. Receive the callback.
6. Verify callback authenticity and transaction details.
7. Match the callback to the local payment.
8. Confirm amount, currency, merchant reference, and status.
9. Process the payment exactly once.
10. Activate the subscription or grant the purchased credits.
11. Record the payment event and credit transaction.
12. Reconcile uncertain or missing callbacks.

Never grant credits based solely on a browser redirect.

The current JazzCash merchant contract, signatures, endpoint URLs, field names, and sandbox behavior must be verified before production integration.

## 19. Email and SMS

Email use cases:

- Account verification.
- Password reset.
- Security alerts.
- Request and connection notifications.
- Payment receipts.
- Export ready notifications.
- Deletion confirmation.

SMS use cases:

- OTP.
- Essential security notifications.
- Critical account notifications where configured.

Do not send private profile details or message contents in generic SMS notifications.

## 20. Push notifications

Support:

- Device registration.
- Multiple devices per account.
- Token replacement.
- Invalid token revocation.
- Notification preferences.
- Generic notification payloads.
- Deep links that still require server-side authorization.

## 21. Object storage

Use a storage abstraction with local filesystem support and production private object storage.

Recommended storage groups:

- Profile photos.
- Identity verification documents.
- Message attachments.
- Shared documents.
- Moderation evidence.
- Data exports.

Apply separate permissions and retention policies. Never store sensitive files in a public bucket by default.

## 22. Integration configuration

Use centralized environment/configuration settings for:

- S3/object storage.
- Email.
- SMS/OTP.
- JazzCash.
- Push notifications.
- Redis.
- Celery/background jobs.

Production credentials must be injected securely. Never commit `.env` files containing real secrets.

## 23. API acceptance criteria

- Every endpoint has an OpenAPI schema.
- All protected endpoints require appropriate authentication.
- Object-level authorization is tested.
- Pagination and error formats are consistent.
- Financial operations are idempotent.
- Payment callbacks are verified.
- Private files are not exposed publicly.
- Provider integrations have mock/test implementations.
- Integration failures are logged without exposing secrets.
- Web and mobile clients use the same API contracts.