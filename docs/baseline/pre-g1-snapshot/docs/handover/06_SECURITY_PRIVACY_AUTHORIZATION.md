# Matermonial — Security, Privacy and Authorization Requirements

**Version:** 1.0  
**Date:** 11 November 2026

## 1. Security objectives

The platform processes highly personal matrimonial information. Security and privacy must be enforced in the backend, not merely through frontend controls.

The system must protect:

- Account credentials.
- Phone numbers and email addresses.
- Identity verification information.
- Date of birth.
- Profile and family information.
- Photographs.
- Income and employment information.
- Private preferences.
- Conversations.
- Shared documents.
- Payment and credit history.
- Family-manager authorization.
- Moderation evidence.
- Data exports.

## 2. Authentication security

- Use Django's supported password hashing.
- Never store plaintext passwords.
- Normalize phone numbers to E.164.
- Enforce rate limits for registration, login, OTP, and password reset.
- Store OTPs as hashes.
- Expire OTPs after the configured validity period.
- Enforce resend cooldown and attempt limits.
- Do not disclose whether an account exists through sensitive recovery responses.
- Revoke sessions/tokens after password reset or security-sensitive events as appropriate.
- Record login attempts and security events.
- Protect refresh tokens if JWT is used.
- Avoid storing tokens in browser local storage where a safer supported session design is available.
- Use platform secure storage for mobile credentials.

## 3. OTP security

Initial defaults:

- Validity: 5 minutes.
- Resend cooldown: 60 seconds.
- Maximum verification attempts: 5.
- Maximum send attempts: 5 per hour, configurable.

Additional requirements:

- Use cryptographically secure random OTP generation.
- Store only a keyed hash or secure hash suitable for verification.
- Compare securely.
- Invalidate OTP after successful verification.
- Prevent concurrent verification from consuming the same OTP multiple times.
- Rate-limit by account, phone, IP, and other appropriate signals.
- Do not log OTP plaintext.
- Do not include OTP values in analytics or audit metadata.

## 4. Identity verification security

- Store identity documents privately.
- Use separate access permissions from ordinary profile media.
- Limit access to authorized verification reviewers.
- Log document views, downloads, and review decisions.
- Use protected HMAC fingerprints for duplicate-document detection.
- Never store plain hashes of predictable identity numbers as the duplicate-detection mechanism.
- Avoid placing identity numbers in logs.
- Define retention and deletion policies.
- Allow resubmission after rejection according to the review workflow.
- Require elevated approval for manual duplicate-detection overrides.
- Do not expose internal reviewer notes to ordinary profile viewers.

## 5. Account and profile authorization

Authentication identifies an account. It does not automatically authorize access to every profile.

Every operation involving a matrimonial profile must resolve:

1. The authenticated account.
2. The requested profile.
3. Whether the account owns the profile or has an active authorization.
4. Whether the required permission is granted.
5. Whether the authorization is expired, paused, or revoked.
6. Whether the target profile is eligible for the action.
7. Whether blocking or privacy rules prevent the action.
8. Whether additional verification is required.

Do not rely on a frontend-supplied profile ID.

## 6. Family-manager authorization

- The owner creates authorization.
- The manager accepts it.
- Permission is scoped to a specific profile.
- Permission groups are templates only.
- Individual permissions are enforced by the backend.
- Sensitive permissions are owner-only by default.
- The owner can pause, resume, or revoke authorization.
- Paused/revoked/expired authorization immediately loses access.
- Every permission change is audited.
- Sensitive manager actions may require additional verification and owner notification.
- Manager actions record both actual account and represented profile.
- Do not grant access to the owner's account credentials, password, or authentication tokens.

## 7. Object-level authorization

Every private endpoint must check ownership, participation, authorization, and resource state.

Examples:

- A user cannot retrieve another user's private favorite notes.
- A conversation participant cannot access a conversation unrelated to their profile.
- A manager cannot access a profile after authorization revocation.
- A document recipient cannot download a revoked document.
- A blocked profile cannot initiate new communication.
- A hidden profile cannot discover the owner through search.
- An ordinary moderator cannot access unrelated identity documents.
- A support agent cannot read private messages without a specifically approved operational process.

## 8. API security

- Enforce HTTPS in production.
- Validate all request data.
- Apply authentication and permission checks.
- Apply throttling to sensitive endpoints.
- Prevent mass assignment of protected fields.
- Do not accept owner, creator, reviewer, or actor fields blindly from the client.
- Set actor fields from the authenticated request context.
- Use secure CORS configuration.
- Use appropriate CSRF protection for cookie-based authentication.
- Avoid overly permissive production CORS.
- Prevent insecure direct object reference vulnerabilities.
- Do not reveal private resource existence unnecessarily.
- Keep error messages useful but non-disclosing.

## 9. Privacy classification

Classify data into access levels:

### Public or discoverable

Only fields explicitly approved for profile discovery, such as selected display name, age, general location, profile description, and approved photographs.

### Authenticated limited

Information available to verified or eligible platform users under profile visibility rules.

### Connection-only

Information available only to connected profiles where the owner has permitted disclosure.

### Owner-only

Private notes, account settings, hidden-profile list, detailed visitor controls, and other owner-controlled information.

### Manager-authorized

Information available only to managers with explicit permission for the represented profile.

### Restricted operational

Identity documents, internal moderation evidence, security investigations, sensitive audit details, and private provider responses.

Serializers must use explicit field allowlists. Do not serialize entire model objects.

## 10. Private media security

- Store private files outside public web roots.
- Use private object storage in production.
- Use opaque storage keys.
- Do not store public permanent URLs in database fields.
- Generate short-lived signed URLs or serve through an authorization-controlled endpoint.
- Check permission before generating a URL.
- Apply content-type, size, and extension validation.
- Inspect file content rather than trusting the extension.
- Scan uploaded files where supported.
- Use separate storage permissions for identity documents, profile photos, shared documents, attachments, evidence, and exports.
- Revoke database permissions immediately when access is withdrawn.
- Recognize that a previously issued signed URL may remain valid until its expiry unless proxy delivery or another revocation mechanism is used.
- Never claim that remote deletion can recall a file already downloaded by another person.

## 11. Blocking and hiding privacy

Blocking and Hide My Profile From are separate mechanisms.

### Blocking

- Unilateral.
- No notification to the blocked person.
- Prevents discovery, new requests, and communication.
- Disables applicable media/document access.
- Preserves history.

### Hide My Profile From

- Unilateral.
- No notification.
- Prevents search/recommendation discovery and new interests/requests.
- Does not terminate an existing accepted connection.
- Does not automatically terminate existing communication.
- Does not automatically revoke existing photo/document permissions.

The backend must apply these rules consistently across search, recommendations, requests, conversations, and media access.

## 12. Financial security

- Use Decimal for monetary values.
- Use integer quantities for credits.
- Store currency explicitly.
- Keep subscription and purchased balances separate.
- Keep an append-only credit ledger.
- Lock relevant rows during balance deductions.
- Prevent negative balances.
- Use unique idempotency keys.
- Validate payment callbacks.
- Verify merchant reference, amount, currency, gateway identity, and status.
- Never grant credits from frontend assertions.
- Record sanitized gateway responses.
- Do not store prohibited payment credentials.
- Reconcile uncertain payments.
- Use compensating transactions for corrections and refunds.
- Require additional approval for manual credit adjustments.

## 13. Notification security

- Use generic SMS and push content.
- Do not include OTPs in ordinary notification history.
- Do not include private profile details in lock-screen notifications.
- Do not include conversation contents or documents in push payloads.
- Mask phone/email destinations in delivery logs.
- Sanitize provider responses.
- Keep security notifications enabled.
- Protect notification action URLs with normal authentication and authorization.

## 14. Messaging security

- Enforce active connection status.
- Enforce block restrictions.
- Verify the sender profile belongs to the account or is manager-authorized.
- Record actual sender account.
- Validate attachment content and size.
- Scan files where supported.
- Restrict message and attachment retrieval to participants.
- Do not expose internal support or moderation notes as conversation messages.
- Preserve legitimate message history according to retention policy.

## 15. Administrative security

- Use least-privilege admin roles.
- Require MFA for production administrative accounts.
- Separate support, moderation, finance, verification, and system administration permissions.
- Restrict access to identity documents.
- Audit sensitive administrative reads and writes.
- Require dual approval for configured high-risk actions.
- Prevent moderators from reviewing cases with conflicts of interest.
- Avoid shared administrator accounts.
- Review inactive and expired admin roles.
- Store admin login and access history.

## 16. Audit requirements

Audit:

- Authentication and security events.
- Profile access by family managers.
- Authorization creation, changes, pause, resume, and revocation.
- Sensitive privacy changes.
- Identity verification decisions.
- Request and connection state transitions.
- Credit and payment changes.
- Document sharing and access.
- Moderation actions and appeals.
- Data export and download.
- Account deletion.
- Administrative configuration changes.
- Feature-flag changes.
- Sensitive administrative access.

Audit logs must be append-only to normal application users. Corrections must be represented as new events.

Never put passwords, OTP plaintext, access tokens, private file contents, or full message bodies into general audit records.

## 17. Data export security

- Require identity confirmation.
- Export only the requester's authorized data.
- Exclude other users' private information.
- Exclude internal moderation evidence and identity verification documents by default.
- Store ZIP files privately.
- Use temporary signed links.
- Apply seven-day export availability.
- Use 24-hour link expiry.
- Log downloads.
- Delete expired export files according to retention policy.

## 18. Account deletion security

- Require identity confirmation.
- Use a 30-day recovery period.
- Disable public visibility and new activity during recovery.
- Revoke sessions and manager authorizations when processing begins.
- Use idempotent deletion steps.
- Apply documented legal and security retention holds.
- Preserve other users' legitimate conversation history as appropriate.
- Do not transfer profile ownership automatically.
- Record every deletion step and result.
- Delete or anonymize remaining data according to retention policy.

## 19. Logging and secret management

Never log:

- Passwords.
- OTP plaintext.
- Access or refresh tokens.
- Full identity numbers.
- Private document contents.
- Unmasked payment credentials.
- Private signed URLs.
- Full private message content.

Use secure deployment secret management or environment injection.

Never commit production `.env` files, credentials, certificates, or API keys.

## 20. Security testing

Required tests include:

- Unauthorized access.
- Cross-account data access.
- IDOR attempts.
- Manager permission escalation.
- Expired/revoked manager authorization.
- Blocked profile access.
- Hidden-profile discovery.
- Private document access after revocation.
- Expired signed URL behavior.
- OTP brute-force/rate-limit behavior.
- Payment callback forgery.
- Duplicate callback processing.
- Concurrent credit deductions.
- Negative balance prevention.
- Moderator conflict restrictions.
- Unauthorized export access.
- Account deletion recovery and retention holds.

## 21. Security release gate

Do not release to production until:

- Authentication and authorization tests pass.
- Sensitive data is not exposed by serializers.
- Private storage is verified.
- Payment callback verification is implemented.
- Financial concurrency tests pass.
- Admin MFA and least privilege are configured.
- Secrets are removed from source control.
- Backup restoration is tested.
- Logging redaction is verified.
- High-risk security findings are resolved or formally accepted.