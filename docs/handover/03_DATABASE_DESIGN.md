# Matermonial — Database Design: 16 Modules

**Version:** 1.0  
**Date:** 11 November 2026  
**Database:** PostgreSQL  
**Primary key convention:** UUID for major domain entities (UUIDv7 for partitioned log tables, §22.15)  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-03, OD-04, OD-05, OD-06, OD-07, OD-09; OPEN legacy ODs (doc 13 series): OD-005; PROPOSED TRs: TR-01, TR-03, TR-06, TR-07, TR-10, TR-11, TR-17, TR-23, TR-24; §22 structures are TR content per doc 19. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**G1 note:** structures added or changed by the approved baseline are in **§22**, which wins over §1–§21 where they differ.

## 1. General database standards

1. Use UUID primary keys for major business entities.
2. Use `created_at` and `updated_at` where appropriate.
3. Use UTC-aware timestamps.
4. Use `DecimalField` for money and income values.
5. Use integer fields for whole-number quantities and earning bounds.
6. Use database constraints for unique business invariants.
7. Use foreign keys with deliberate deletion behavior.
8. Prefer explicit status fields and transition services.
9. Use append-only history tables for important business transitions.
10. Avoid storing derived values that can be reliably calculated, unless a snapshot is required for historical correctness.
11. Do not store passwords, OTPs, payment secrets, or private file contents in ordinary text fields.
12. Use JSON fields only for flexible metadata, sanitized provider responses, or configurable values—not as a substitute for relational design.
13. Apply indexes based on actual access patterns.
14. Use database transactions and row-level locking for financial and concurrency-sensitive operations.
15. Define deletion, anonymization, retention, and legal-hold behavior explicitly.

## 2. Module 01 — Accounts and Authentication

### 2.1 User

Use a custom Django user model based on `AbstractBaseUser` and a custom user manager.

Principal fields:

- `id`: UUID.
- `phone_number`: normalized E.164, unique.
- `email`: nullable, unique when supplied, **case-insensitively**; stored trimmed and lower-cased (DR-2026-11-18-G4-9).
- `password`: Django password hash.
- `first_name`.
- `last_name`.
- `date_joined`.
- `is_active`.
- `is_staff`.
- `is_superuser`.
- `is_phone_verified` (name aligned with §22.1 row 5; DR-2026-11-18-G4-9).
- `is_email_verified` (same naming convention; DR-2026-11-18-G4-9).
- `deactivated`: Boolean, default false.
- `deactivated_reason`: nullable text.
- `created_at`.
- `created_by`: nullable user FK where applicable.
- `updated_at`.
- `updated_by`: nullable user FK where applicable.

Do not expose password hashes through APIs.

### 2.2 AccountSecurityEvent

> **G1 (DCR-25, DCR-35, DCR-60, DCR-67, DCR-76):** the authoritative definition is §22.2. AccountSecurityEvent is append-only and stores pseudonyms and encrypted envelopes, not `user`, `ip_address` or `user_agent` in plaintext. The original field list below is kept for history.

Fields:

- `id`.
- `user`: nullable FK for pre-account events.
- `event_type`.
- `result`.
- `ip_address`.
- `user_agent`.
- `description`.
- `occurred_at`.

Examples: failed login, password reset, OTP verification failure, suspicious activity.

### 2.3 LoginHistory

> **G1 (DCR-25): retired.** `LoginHistory` is not implemented. Session state lives in `AuthSession` and login, session and security events in `AccountSecurityEvent` (§22.2). The user's "login and device history" view is a selector over both. The original field list below is kept for history.

Fields:

- `id`.
- `user`.
- `session_identifier_hash` or safe session reference.
- `login_at`.
- `logout_at`.
- `ip_address`.
- `user_agent`.
- `device_name`.
- `browser_name`.
- `operating_system`.
- `approximate_location`.
- `status`.

Do not store raw authentication tokens in history.

### 2.4 AccountDeletionRequest

The dedicated deletion workflow is defined in Module 14. Keep one authoritative deletion-request model rather than creating conflicting duplicate models in this module.

### 2.5 OTP requirements

Use a `PhoneVerification` entity in Module 04.

Initial configurable defaults:

- OTP validity: 5 minutes.
- Resend cooldown: 60 seconds.
- Verification attempts: maximum 5.
- OTP requests: maximum 5 per hour, subject to abuse controls.
- Store OTP hash only.
- Never log OTP plaintext.

## 3. Module 02 — Profiles

### 3.1 MatrimonialProfile

Fields:

- `id`: UUID.
- `owner`: OneToOne FK to User.
- `profile_code`: unique public/internal reference.
- `profile_status`: DRAFT, PENDING_REVIEW, ACTIVE, PAUSED, SUSPENDED, CLOSED.
- `visibility_status`: HIDDEN, VISIBLE_IN_MATCH_SEARCH, LIMITED_VISIBILITY.
- `verification_status`.
- `completion_percentage`.
- `is_active`.
- `created_at`, `created_by`.
- `updated_at`, `updated_by`.

An account may own one personal profile. An account may separately manage other profiles through Module 05.

### 3.2 ProfileBasicInfo

OneToOne relationship with MatrimonialProfile.

Fields:

- `full_name`.
- `date_of_birth`.
- `gender`.
- `marital_status`.
- `religion`.
- `community`.
- `caste_or_subcast`.
- `nationality`.

The full date of birth must not be publicly exposed.

### 3.3 ProfileLocation

OneToOne relationship with MatrimonialProfile.

Fields:

- `country`.
- `state_or_province`.
- `city`.
- `area_or_locality`.
- `residence_type`.
- `show_location`.

Location display must respect privacy settings.

### 3.4 ProfileFamilyDetails

Fields:

- `profile`.
- `father_occupation`.
- `mother_occupation`.
- `family_type`.
- `family_values`.
- `number_of_brothers`.
- `number_of_sisters`.
- `family_description`.

Use nullable fields where the user may not wish to disclose information.

### 3.5 ProfileEducation

Many education records per profile.

Fields:

- `profile`.
- `qualification`.
- `field_of_study`.
- `institution`.
- `country`.
- `completion_year`.
- `is_current`.
- `description`.

### 3.6 ProfileProfession

Fields:

- `profile`.
- `employment_status`.
- `profession`.
- `job_title`.
- `employer_or_business_name`.
- `income_amount`: Decimal.
- `income_currency`.
- `income_frequency`.
- `show_income`.
- `description`.

### 3.7 ProfileLifestyle

Fields:

- `profile`.
- `height`.
- `diet`.
- `smoking_status`.
- `drinking_status`.
- `exercise_habit`.
- `description`.

### 3.8 ProfileLanguage

Many-to-one relationship with profile.

Fields:

- `profile`.
- `language`.
- `proficiency`.
- `is_native`.

Prevent duplicate language records for the same profile where appropriate.

### 3.9 ProfilePhoto

Fields:

- `profile`.
- `storage_key`.
- `photo_type`.
- `is_primary`.
- `moderation_status`.
- `uploaded_at`.
- `updated_at`.
- `deleted_at`.

The storage key must not be a public URL. Private access is governed by Module 10.

## 4. Module 03 — Partner Preferences

### 4.1 PartnerPreference

OneToOne relationship with MatrimonialProfile.

Fields:

- `profile`.
- `minimum_age`.
- `maximum_age`.
- `preferred_gender`.
- `preferred_marital_status`.
- `religion`.
- `community`.
- `caste_or_subcast`.
- `nationality`.
- `own_house`: nullable Boolean.
- `job`: nullable Boolean.
- `business`: nullable Boolean.
- `minimum_earning`: nullable Integer.
- `maximum_earning`: nullable Integer.
- `earning_currency`.
- `earning_frequency`.
- `residence_type`.
- `additional_requirements`.
- `created_at`.
- `updated_at`.

Validation:

- Minimum age must not exceed maximum age.
- Minimum earning must not exceed maximum earning.
- Currency and frequency must be handled consistently.
- NULL Boolean means no preference.

### 4.2 Multi-value preference models

Create separate models:

- `PartnerPreferenceLocation`
- `PartnerPreferenceEducation`
- `PartnerPreferenceLanguage`
- `PartnerPreferenceReligion`

Each should reference PartnerPreference and store one preferred value or structured reference.

Avoid comma-separated values in a single text field.

## 5. Module 04 — Verification

### 5.1 PhoneVerification

Fields:

- `user`: nullable FK for pre-registration verification.
- `phone_number`.
- `purpose`.
- `code_hash`.
- `created_at`.
- `expires_at`.
- `verified_at`.
- `attempt_count`.
- `resend_count`.
- `status`.
- `provider_reference`.

### 5.2 IdentityVerification

Fields:

- `user`.
- `profile`: nullable FK where applicable.
- `verification_type`.
- `status`: NOT_SUBMITTED, PENDING_REVIEW, UNDER_REVIEW, APPROVED, REJECTED, RESUBMISSION_REQUIRED, CANCELLED.
- `submitted_at`.
- `reviewed_at`.
- `reviewer`.
- `rejection_reason`.
- `resubmission_allowed`.

### 5.3 VerificationDocument

Fields:

- `verification`.
- `document_type`.
- `storage_key`.
- `status`.
- `uploaded_at`.
- `reviewed_at`.
- `reviewer`.
- `rejection_reason`.
- `deleted_at`.

### 5.4 VerificationReview

Fields:

- `verification`.
- `reviewer`.
- `decision`.
- `reason`.
- `reviewed_at`.
- `internal_notes`.

### 5.5 IdentityDocumentFingerprint

Fields:

- `verification`.
- `document_type`.
- `protected_hmac_fingerprint`.
- `status`.
- `created_at`.

Use a protected keyed HMAC fingerprint. Never use a plain hash of predictable identity-document numbers.

## 6. Module 05 — Family Management

### 6.1 ProfileManagerAuthorization

Fields:

- `profile`.
- `manager`: User FK.
- `permission_group`: nullable FK.
- `status`: PENDING, ACTIVE, PAUSED, EXPIRED, REVOKED, REJECTED.
- `invited_at`.
- `accepted_at`.
- `authorized_at`.
- `expires_at`: nullable.
- `paused_at`.
- `revoked_at`.
- `reason`.
- `created_at`.
- `updated_at`.

Rules:

- Owner creates invitation.
- Manager must accept.
- Manager cannot authorize themselves.
- Prevent duplicate active/pending authorization for the same manager/profile.
- Expiry is optional; no expiry is the default.
- Pause, resume, and revoke actions must be audited.

### 6.2 ManagerPermissionGroup

Fields:

- `name`.
- `code`.
- `description`.
- `is_system_default`.
- `is_active`.

Starter templates:

- Standard Manager.
- Communication Manager.
- Advanced Manager.

### 6.3 ManagerPermission

Fields:

- `code`.
- `name`.
- `description`.
- `is_sensitive`.
- `is_active`.

### 6.4 AuthorizationPermission

Fields:

- `authorization`.
- `permission`.
- `is_granted`.
- `granted_by`.
- `granted_at`.
- `updated_at`.

Enforce uniqueness for authorization and permission.

### 6.5 ManagerAuthorizationHistory

Append-only fields:

- `authorization`.
- `action`.
- `performed_by`.
- `previous_values`.
- `new_values`.
- `reason`.
- `created_at`.

### 6.6 ManagerActionLog

Fields:

- `authorization`.
- `profile`.
- `manager`.
- `action_type`.
- `target_model`.
- `target_id`.
- `description`.
- `ip_address`.
- `user_agent`.
- `created_at`.

### 6.7 ProfileAccessHistory

Fields:

- `profile`.
- `authorization`.
- `manager`.
- `accessed_at`.
- `device`.
- `browser`.
- `ip_address`.
- `approximate_location`.
- `access_type`.

This is distinct from account login history.

### 6.8 SensitiveActionVerification

Fields:

- `authorization`.
- `profile`.
- `requested_by`.
- `action_type`.
- `status`.
- `verification_method`.
- `requested_at`.
- `verified_at`.
- `expires_at`.
- `verification_reference`.

## 7. Module 06 — Matching and Search

### 7.1 ProfileFavorite

Fields:

- `user`.
- `profile`.
- `private_note`.
- `created_at`.
- `updated_at`.

Unique constraint: user + profile.

Private notes are account-specific.

### 7.2 ProfileView

Fields:

- `viewer_user`.
- `viewer_profile`: nullable represented profile.
- `target_profile`.
- `viewed_at`.
- `billing_window_start`.
- `is_billable`.
- `credit_transaction`: nullable FK.
- `access_type`.
- `created_at`.

- `billing_account` (G1, DCR-14): the owner account of the represented profile performing the view.

The **billing account is the owner account of the represented profile** [DECIDED]. A manager's personal account is never charged for a delegated view, and the owner and all of their managers share one 24-hour window per (billing account, target) [DECIDED]. Private browsing never changes ProfileView (§22.6).

### 7.3 SearchHistory

Optional MVP model for explicitly saved searches only.

Fields:

- `user`.
- `search_name`.
- `filters` JSON.
- `created_at`.
- `updated_at`.

Do not persist every ordinary search request.

### 7.4 MatchingInteraction

Defer unless a defined MVP analytics or recommendation use case requires it.

## 8. Module 07 — Interests and Matrimonial Requests

### 8.1 MatrimonialRequest

Fields:

- `id`: UUID.
- `sender_profile`.
- `receiver_profile`.
- `status`: PENDING, ACCEPTED, DECLINED, WITHDRAWN, EXPIRED, CANCELLED.
- `message`.
- `sent_at`.
- `expires_at`.
- `responded_at`.
- `withdrawn_at`.
- `closed_at`.
- `credit_transaction`: nullable FK.
- `created_by`: actual User.
- `updated_by`: actual User.
- `created_at`.
- `updated_at`.

Rules:

- Sender and receiver must differ.
- Accepted only by recipient or authorized manager.
- Withdrawn only by sender or authorized manager.
- Request expiry is three calendar months.
- Duplicate active requests in either direction are prohibited.
- Preserve final records.

### 8.2 RequestHistory

Append-only fields:

- `request`.
- `action`.
- `previous_status`.
- `new_status`.
- `performed_by`.
- `performed_for_profile`.
- `reason`.
- `metadata`.
- `created_at`.

### 8.3 RequestCooldown

> **G1 (DCR-19):** generalised into `DirectionalCooldown` (§22.7), covering both interest and request cooldowns. The rules below still apply.

Fields:

- `sender_profile`.
- `receiver_profile`.
- `source_request`.
- `reason`: DECLINED or EXPIRED.
- `starts_at`.
- `ends_at`.
- `created_at`.

Cooldown applies only from the original sender to the original recipient for 30 days.

No cooldown after withdrawal or administrative cancellation by default.

## 9. Module 08 — Connections and Relationship Progress

### 9.1 ProfileConnection

Fields:

- `id`: UUID.
- `profile_one`.
- `profile_two`.
- `request`: nullable OneToOne/FK to accepted request as designed.
- `status`: ACTIVE, PAUSED, COMPLETED, CLOSED.
- `connected_at`.
- `paused_at`.
- `paused_by_profile`, `pause_reason`, `closed_from_status` (G1, §22.8).
- `closed_at`.
- `completed_at`.
- `closed_by`.
- `closure_reason`.
- `closure_notes`.
- `created_at`.
- `updated_at`.

Normalize profile ordering so the same pair cannot create duplicate connections.

Use a unique constraint on the normalized pair.

### 9.2 ConnectionHistory

Append-only fields:

- `connection`.
- `action`.
- `previous_status`.
- `new_status`.
- `performed_by`.
- `performed_for_profile`.
- `reason`.
- `metadata`.
- `created_at`.

### 9.3 RelationshipProgress

OneToOne relationship with connection.

Fields:

- `connection`.
- `stage` (G1, DCR-37; formerly `status`): REQUEST_ACCEPTED, INITIAL_COMMUNICATION, DISCUSSION_IN_PROGRESS, MEETING_PLANNED, MEETING_COMPLETED, PROPOSAL_SERIOUS_DISCUSSION, ENGAGED. `CLOSED` is not stored; the "Closed" label is derived from the connection (§22.8, OD-06i OPEN).
- `updated_by`.
- `updated_for_profile`.
- `updated_at`.
- `shared_notes`.

### 9.4 RelationshipProgressHistory

Fields:

- `relationship_progress`.
- `previous_status`.
- `new_status`.
- `notes`.
- `performed_by`.
- `performed_for_profile`.
- `created_at`.

## 10. Module 09 — Messaging and Shared Documents

### 10.1 Conversation

OneToOne relationship with ProfileConnection.

Fields:

- `connection`.
- ~~`status`~~ removed in G1 (DCR-05): conversation state is derived from the connection (§22.9, doc 15 §8).
- `created_at`.
- `updated_at`.
- `last_message_at`.
- `closed_at`.
- `closure_reason`.

### 10.2 ConversationParticipant

Fields:

- `conversation`.
- `profile`.
- `joined_at`.
- `left_at`.
- `is_active`.

Unique constraint: conversation + profile.

MVP: exactly two profile participants.

### 10.3 Message

Fields:

- `conversation`.
- `sender_profile`.
- `sender_user`.
- `message_type`: TEXT or SYSTEM.
- `content`.
- `reply_to`: nullable self-FK.
- `sent_at`.
- `edited_at`.
- `deleted_at`.
- `created_at`.

Record the actual manager account when sending on behalf of a profile.

### 10.4 MessageAttachment

Fields:

- `message`.
- `storage_key`.
- `filename`.
- `mime_type`.
- `file_size`.
- `scan_status`.
- `uploaded_at`.
- `deleted_at`.

### 10.5 MessageReadReceipt

Fields:

- `message`.
- `reader_profile`.
- `read_by_user`.
- `read_at`.

Unique constraint: message + reader profile.

### 10.6 SharedDocument

Fields:

- `owner_profile`.
- `uploaded_by`.
- `document_type`.
- `title`.
- `description`.
- `storage_key`.
- `filename`.
- `mime_type`.
- `file_size`.
- `scan_status`.
- `status`: ACTIVE, REVOKED, DELETED.
- `uploaded_at`.
- `deleted_at`.

Shared documents are distinct from verification documents and message attachments.

### 10.7 DocumentAccessPermission

Fields:

- `document`.
- `recipient_profile`.
- `granted_by`.
- `granted_at`.
- `expires_at`.
- `revoked_at`.
- `revoked_by`.
- `status`: ACTIVE, EXPIRED, REVOKED.
- `created_at`.
- `updated_at`.

Unique constraint: document + recipient profile **among ACTIVE permissions** (partial unique `WHERE status = 'ACTIVE'`, G1 DCR-15), so a new permission can be issued after expiry or revocation.

### 10.8 DocumentAccessHistory

Fields:

- `document`.
- `permission`.
- `accessed_by`.
- `accessed_for_profile`.
- `action`: UPLOADED, SHARED, VIEWED, DOWNLOADED, REVOKED.
- `ip_address`.
- `user_agent`.
- `created_at`.

## 11. Module 10 — Privacy and Media Access

### 11.1 ProfilePrivacySettings

OneToOne relationship with profile.

Fields:

- `profile`.
- `profile_visibility`.
- `photo_visibility`.
- `show_contact_information`.
- `show_location`.
- `allow_profile_views`.
- `allow_photo_requests`.
- `private_browsing`.
- `allow_recommendations`.
- `updated_by`.
- `updated_at`.

### 11.2 ProfileBlock

Fields:

- `blocker_profile`.
- `blocked_profile`.
- `created_at`.
- `reason`: optional internal reason.

Unique constraint: blocker + blocked. A block is unilateral.

### 11.3 HiddenProfile

Fields:

- `owner_profile`.
- `hidden_profile`.
- `created_at`.

Unique constraint: owner + hidden profile.

This is distinct from ProfileBlock.

### 11.4 PhotoAccessRequest

Fields:

- `requester_profile`.
- `owner_profile`.
- `status`.
- `message`.
- `requested_at`.
- `responded_at`.

### 11.5 PhotoAccessPermission

Fields:

- `owner_profile`.
- `recipient_profile`.
- `granted_by`.
- `granted_at`.
- `expires_at`.
- `revoked_at`.
- `revoked_by`.
- `status`.

Support seven-day, thirty-day, and manual expiration.

G1 (DCR-15): partial unique on (`owner_profile`, `recipient_profile`) `WHERE status = 'ACTIVE'`.

### 11.6 VisitorHistory

Fields:

- `owner_profile`.
- `visitor_profile`: nullable for private browsing.
- `visitor_user`: nullable where needed.
- `visited_at`.
- `access_type`.
- `is_private_visit`.

Do not expose private-visitor identity through normal visitor-history APIs.

### 11.7 VisitorHistoryRemoval

Fields:

- `owner_profile`.
- `visitor_history`.
- `removed_by`.
- `removed_at`.

Removal affects the visible history, not security/audit records. The visitor may appear again later.

## 12. Module 11 — Subscriptions and Credits

### 12.1 SubscriptionPlan

Fields:

- `id`: UUID.
- `name`.
- `code`.
- `description`.
- `duration_days`.
- `price`: Decimal.
- `currency`.
- `is_free`.
- `is_active`.
- `display_order`.
- `created_at`, `created_by`.
- `updated_at`, `updated_by`.

### 12.2 SubscriptionPlanBenefit

Fields:

- `plan`.
- `benefit_code`.
- `name`.
- `value` JSON.
- `enabled`.
- `created_at`.
- `updated_at`.

Financial allowances must also be issued through explicit allowance records.

### 12.3 UserSubscription

Fields:

- `user`.
- `plan`.
- `status`: PENDING, ACTIVE, EXPIRED, CANCELLED, PAYMENT_FAILED.
- `starts_at`.
- `ends_at`.
- `grace_period_ends_at`.
- `purchase_price_snapshot`.
- `currency_snapshot`.
- `billing_period_start`.
- `billing_period_end`.
- `activated_at`.
- `cancelled_at`.
- `expired_at`.
- `cancellation_reason`.
- `created_at`.
- `updated_at`.

Only one active paid subscription per account.

### 12.4 SubscriptionBillingPeriod

Fields:

- `subscription`.
- `period_start`.
- `period_end`.
- `status`: PENDING, ACTIVE, COMPLETED, EXPIRED.
- `created_at`.
- `updated_at`.

Prevent overlapping active billing periods.

### 12.5 CreditWallet

One per User.

Maintain separate balances for the purchased buckets:

- Purchased request credits (`purchased_request_balance`).
- Purchased profile-view credits (`purchased_view_balance`).

Subscription request and profile-view credits are tracked per `CreditAllowance` row (G1, DCR-31). Balances are projections of the ledger, updated only in the same transaction as the matching ledger row. The ledger remains the authoritative history (§22.1 rows 8–9, §22.11).

### 12.6 CreditAllowance

Fields:

- `user`.
- `subscription`.
- `billing_period`.
- `credit_type`: REQUEST or PROFILE_VIEW.
- `granted_amount`.
- `remaining_amount`.
- `expires_at`.
- `status`: ACTIVE, EXHAUSTED, EXPIRED.
- `created_at`.
- `updated_at`.

### 12.7 CreditTransaction

Append-only financial ledger fields:

- `user`.
- `credit_type`: REQUEST or PROFILE_VIEW.
- `source`: SUBSCRIPTION_ALLOWANCE, PURCHASED, ADMIN_ADJUSTMENT, REFUND.
- `transaction_type`: CREDIT, DEBIT, EXPIRY, ADJUSTMENT.
- `amount`.
- `bucket_balance_after`.
- `subscription`: nullable.
- `allowance`: nullable.
- `payment`: nullable.
- `related_profile`: nullable.
- `performed_by`: nullable.
- `reference_type`.
- `reference_id`.
- `idempotency_key`.
- `description`.
- `created_at`.

Do not update or delete historical transactions. Corrections require compensating transactions.

> **G1 (DCR-31, DCR-56, DCR-65, DCR-70):** the ledger is extended with a `CreditOperation` header, `operation_kind`, `direction` and `entry_type` columns and the refund structures in §22.11, which govern where they differ from this list.

### 12.8 CreditPackage

Fields:

- `name`.
- `code`.
- `credit_type`.
- `quantity`.
- `price`.
- `currency`.
- `is_active`.
- `display_order`.
- `created_at`.
- `updated_at`.

### 12.9 CreditPurchase

Fields:

- `user`.
- `package`.
- `package_name_snapshot`.
- `quantity_snapshot`.
- `price_snapshot`.
- `currency_snapshot`.
- `status`.
- `payment`.
- `created_at`.
- `updated_at`.

### 12.10 PaymentTransaction

Fields:

- `user`.
- `purpose`: SUBSCRIPTION or CREDIT_PURCHASE.
- `subscription`: nullable.
- `credit_purchase`: nullable.
- `gateway`.
- `gateway_transaction_id`.
- `merchant_reference`.
- `amount`.
- `currency`.
- `status`.
- `payment_method`.
- `sanitized_gateway_response`.
- `created_at`.
- `updated_at`.
- `failure_reason`.

### 12.11 PaymentWebhookEvent

Fields:

- `payment`.
- `gateway_event_id`.
- `event_type`.
- `sanitized_payload`.
- `signature_verified`.
- `processing_status`.
- `attempt_count`.
- `received_at`.
- `processed_at`.
- `last_error`.

### 12.12 SubscriptionChangeHistory

Fields:

- `subscription`.
- `action`.
- `old_plan`.
- `new_plan`.
- `actor`.
- `reason`.
- `metadata`.
- `created_at`.

## 13. Module 12 — Notifications

### 13.1 NotificationType

Fields:

- `code`.
- `name`.
- `description`.
- `category`.
- `is_enabled`.

### 13.2 NotificationTemplate

Fields:

- `notification_type`.
- `channel`: IN_APP, EMAIL, SMS, PUSH.
- `language`.
- `subject`.
- `title`.
- `body`.
- `is_active`.
- `version`.
- `created_at`.
- `updated_at`.

### 13.3 UserNotificationPreference

One per User.

Fields:

- `user`.
- `email_enabled`.
- `sms_enabled`.
- `push_enabled`.
- `in_app_enabled`.
- `marketing_enabled`.
- `language`.
- `quiet_hours_start`.
- `quiet_hours_end`.
- `timezone`.
- `updated_at`.

Essential security/auth notifications must remain enabled. There is no preference field for them (G1, DCR-23: `security_notifications_enabled` removed).

### 13.4 NotificationCategoryPreference

Fields:

- `user`.
- `category`.
- Per-channel enabled settings.
- `created_at`.
- `updated_at`.

Unique constraint: user + category.

### 13.5 Notification

Fields:

- `recipient_user`.
- `recipient_profile`: nullable.
- `notification_type`.
- `title`.
- `body`.
- `category`.
- `priority`.
- `related_object_type`.
- `related_object_id`.
- `action_url`.
- `safe_metadata`.
- `is_read`.
- `read_at`.
- `created_at`.
- `expires_at`.

### 13.6 NotificationDelivery

Fields:

- `notification`.
- `channel`.
- `destination_masked`.
- `provider`.
- `provider_message_id`.
- `status`: PENDING, PROCESSING, SENT, DELIVERED, FAILED, RETRY_SCHEDULED, CANCELLED.
- `attempt_count`.
- `scheduled_at`.
- `sent_at`.
- `delivered_at`.
- `failed_at`.
- `retry_at`.
- `failure_reason`.
- `created_at`.
- `updated_at`.

### 13.7 NotificationDeliveryAttempt

Fields:

- `delivery`.
- `attempt_number`.
- `status`.
- `provider_response_code`.
- `sanitized_provider_response`.
- `error`.
- `started_at`.
- `completed_at`.

### 13.8 PushDevice

Fields:

- `user`.
- `platform`: ANDROID, IOS, WEB.
- `push_token`.
- `safe_device_identifier`.
- `device_name`.
- `app_version`.
- `is_active`.
- `registered_at`.
- `last_used_at`.
- `revoked_at`.

### 13.9 NotificationPreferenceHistory

Fields:

- `user`.
- `preference_type`.
- `previous_values`.
- `new_values`.
- `actor`.
- `changed_at`.

### 13.10 NotificationOutbox

> **G1 (DCR-22, DCR-68, DCR-84): replaced by `OutboxEvent`** in `common/events` (§22.12). The field list below is kept for history and is not implemented.

Fields:

- `event_type`.
- `aggregate_type`.
- `aggregate_id`.
- `minimal_payload`.
- `status`.
- `idempotency_key`.
- `processing_attempts`.
- `available_at`.
- `processed_at`.
- `last_error`.
- `created_at`.

## 14. Module 13 — Moderation and Reporting

### 14.1 ModerationReport

Fields:

- `reporter_user`.
- `reporter_profile`.
- `reported_user`.
- `reported_profile`.
- `category`.
- `reason`.
- `target_type`.
- `target_id`.
- `status`.
- `priority`.
- `assigned_moderator`.
- `created_at`.
- `updated_at`.
- `resolved_at`.

### 14.2 ModerationReportEvidence

Fields:

- `report`.
- `storage_key` or protected evidence reference.
- `metadata`.
- `uploaded_by`.
- `scan_status`.
- `created_at`.

### 14.3 ModerationCase

Fields:

- `case_code`.
- `primary_report`.
- `target_user`.
- `target_profile`.
- `case_type`.
- `status`.
- `priority`.
- `assigned_moderator`.
- `opened_at`.
- `resolved_at`.
- `closed_at`.
- `summary`.

### 14.4 ModerationCaseReport

Fields:

- `case`.
- `report`.

Unique constraint: case + report.

### 14.5 ModerationAction

Fields:

- `case`.
- `report`: nullable.
- `target_user`.
- `target_profile`.
- `action_type`.
- `reason`.
- `internal_notes`.
- `actor`.
- `effective_at`.
- `expires_at`.
- `reversed_at`.
- `reversed_by`.
- `reversal_reason`.

### 14.6 UserRestriction

Fields:

- `user`.
- `restriction_type`: LOGIN, PROFILE_VISIBILITY, SEARCH, REQUESTS, MESSAGING, PHOTO_UPLOAD, DOCUMENT_SHARING, FULL_ACCOUNT.
- `reason`.
- `moderation_action`.
- `starts_at`.
- `expires_at`.
- `revoked_at`.
- `revoked_by`.
- `is_active`.

### 14.7 ContentModeration

Fields:

- `content_type`.
- `content_id`.
- `owner_user`.
- `owner_profile`.
- `status`: PENDING, APPROVED, FLAGGED, REMOVED, RESTORED.
- `reviewed_by`.
- `reviewed_at`.
- `review_reason`.

Use the ProfilePhoto moderation status as the authoritative photo status; do not maintain contradictory duplicate photo states.

### 14.8 ModerationReview

Fields:

- `case`.
- `reviewer`.
- `decision`.
- `findings`.
- `notes`.
- `reviewed_at`.

### 14.9 ModerationAppeal

Fields:

- `appellant`.
- `moderation_action`.
- `reason`.
- `status`.
- `assigned_reviewer`.
- `submitted_at`.
- `reviewed_at`.
- `decision`.

### 14.10 ModerationAppealEvidence

Fields:

- `appeal`.
- `storage_key`.
- `metadata`.
- `scan_status`.
- `uploaded_at`.

### 14.11 ModerationCaseHistory

Append-only fields:

- `case`.
- `action`.
- `previous_values`.
- `new_values`.
- `performed_by`.
- `created_at`.

### 14.12 ModerationPolicy

Fields:

- `code`.
- `name`.
- `description`.
- `category`.
- `severity`.
- `recommended_action`.
- `is_active`.
- `version`.
- `effective_from`.
- `effective_until`.
- `created_by`.
- `updated_by`.

### 14.13 ModerationAssignmentHistory

Fields:

- `case`.
- `previous_moderator`.
- `new_moderator`.
- `assigned_by`.
- `reason`.
- `created_at`.

## 15. Module 14 — Data Exports and Account Deletion

### 15.1 DataExportRequest

Fields:

- `user`.
- `requested_by`.
- `status`: REQUESTED, IDENTITY_VERIFICATION_REQUIRED, VERIFIED, PROCESSING, COMPLETED, FAILED, EXPIRED, CANCELLED.
- `format`: ZIP_JSON.
- `requested_at`.
- `verified_at`.
- `processing_at`.
- `completed_at`.
- `failed_at`.
- `expires_at`.
- `cancelled_at`.
- `failure_reason`.

### 15.2 DataExportFile

Fields:

- `export_request`: OneToOne.
- `storage_key`.
- `filename`.
- `file_size`.
- `checksum`.
- `mime_type`.
- `status`: GENERATING, READY, DOWNLOADED, EXPIRED, DELETED.
- `generated_at`.
- `expires_at`.
- `last_downloaded_at`.
- `download_count`.
- `deleted_at`.

### 15.3 DataExportSection

Fields:

- `export_request`.
- `section_code`.
- `section_name`.
- `status`.
- `record_count`.
- `completed_at`.
- `error`.

### 15.4 DataExportDownloadHistory

Fields:

- `export_file`.
- `downloader`.
- `ip_address`.
- `user_agent`.
- `downloaded_at`.
- `status`: SUCCESS, FAILED, EXPIRED, DENIED.
- `failure_reason`.

### 15.5 AccountDeletionRequest

Fields:

- `user`.
- `requested_by`.
- `status`: REQUESTED, IDENTITY_VERIFICATION_REQUIRED, PENDING_RECOVERY, CANCELLED, PROCESSING, COMPLETED, REJECTED.
- `reason`.
- `identity_verification_reference`.
- `requested_at`.
- `recovery_period_start`.
- `scheduled_deletion_at`.
- `cancelled_at`.
- `processing_at`.
- `completed_at`.
- `rejection_reason`.
- `created_at`.
- `updated_at`.

G1 (DCR-61): one non-terminal deletion request per user (partial unique index, §22.14).

### 15.6 AccountDeletionStep

Fields:

- `deletion_request`.
- `step_code`.
- `step_name`.
- `status`: PENDING, PROCESSING, COMPLETED, SKIPPED, FAILED.
- `started_at`.
- `completed_at`.
- `error`.
- `retry_count`.

Each step must be idempotent.

### 15.7 DataRetentionPolicy

Fields:

- `category`.
- `retention_days`.
- `retention_action`: DELETE, ANONYMIZE, ARCHIVE, MANUAL_REVIEW.
- `legal_basis`.
- `is_active`.
- `effective_from`.
- `effective_until`.
- `created_by`.
- `updated_by`.

### 15.8 DataRetentionHold

Fields:

- `user`: nullable.
- `object_type`.
- `object_id`.
- `hold_type`: LEGAL, SECURITY_INVESTIGATION, FRAUD_INVESTIGATION, FINANCIAL_COMPLIANCE, OTHER.
- `reason`.
- `status`: ACTIVE, RELEASED.
- `applied_by`.
- `applied_at`.
- `released_by`.
- `released_at`.
- `release_reason`.

### 15.9 AccountDeletionHistory

Append-only fields:

- `deletion_request`.
- `action`.
- `actor`.
- `description`.
- `non_sensitive_metadata`.
- `created_at`.

## 16. Module 15 — Audit Logs and Administrative Management

The following is the recommended implementation baseline. Confirm exact field-level requirements and approval thresholds during implementation.

### 16.1 AuditLog

Central append-only audit stream.

> **G1 (DCR-60, DCR-67, DCR-76):** references are stored as pseudonyms and personal context inside encrypted envelopes, with monthly partitions (§22.15). The field list below is kept for orientation.

Recommended fields:

- `actor_user`.
- `actor_type`.
- `action`.
- `resource_type`.
- `resource_id`.
- `represented_profile`.
- `result`.
- `ip_address`.
- `user_agent`.
- `safe_metadata`.
- `occurred_at`.

Do not store passwords, OTPs, access tokens, full payment credentials, identity-document contents, or full message bodies.

### 16.2 AdminRole

> **G1 (DCR-44):** §16.2–16.5 are the **single source** of administrative authorization; Django Groups and `user_permissions` are not used (§22.15).

- `name`.
- `code`.
- `description`.
- `is_active`.
- `created_at`.
- `updated_at`.

### 16.3 AdminPermission

- `code`.
- `name`.
- `description`.
- `is_sensitive`.
- `is_active`.

### 16.4 AdminRolePermission

- `role`.
- `permission`.

Unique role + permission.

### 16.5 AdminUserRole

- `user`.
- `role`.
- `assigned_by`.
- `assigned_at`.
- `expires_at`.
- `revoked_at`.

### 16.6 AdminAccessHistory

- `admin_user`.
- `event_type`.
- `ip_address`.
- `user_agent`.
- `device`.
- `approximate_location`.
- `occurred_at`.

### 16.7 AdminActionApproval

Recommended for sensitive administrative actions.

- `requested_by`.
- `approved_by`.
- `action_type`.
- `resource_type`.
- `resource_id`.
- `status`.
- `reason`.
- `requested_at`.
- `approved_at`.
- `rejected_at`.

### 16.8 SystemConfiguration

- `key`.
- `value`.
- `value_type`.
- `description`.
- `is_sensitive`.
- `is_active`.
- `updated_by`.
- `updated_at`.

Secrets should remain in the deployment secret manager/environment, not ordinary configuration rows.

### 16.9 SystemConfigurationHistory

- `configuration`.
- `previous_value`.
- `new_value`.
- `changed_by`.
- `reason`.
- `changed_at`.

Sensitive values must be redacted.

### 16.10 FeatureFlag

- `key`.
- `name`.
- `description`.
- `is_enabled`.
- `environment`.
- `configuration`.
- `updated_by`.
- `updated_at`.

### 16.11 FeatureFlagHistory

- `feature_flag`.
- `previous_values`.
- `new_values`.
- `changed_by`.
- `reason`.
- `changed_at`.

## 17. Module 16 — Admin Support and Platform Operations

The following are recommended fields for the three previously discussed entities. Confirm detailed operational requirements while implementing the admin support interface.

### 17.1 AdminSupportCase

- `case_code`.
- `requester_user`.
- `target_profile`: nullable.
- `category`.
- `priority`.
- `status`.
- `assigned_admin`.
- `subject`.
- `description`.
- `created_at`.
- `updated_at`.
- `resolved_at`.
- `closed_at`.

### 17.2 AdminSupportCaseMessage

- `support_case`.
- `author_user`.
- `visibility`: PUBLIC or INTERNAL.
- `body`.
- `attachment_reference`: nullable.
- `created_at`.
- `updated_at`.

Internal messages must never be exposed through user-facing support APIs.

### 17.3 PlatformMaintenanceWindow

- `title`.
- `description`.
- `starts_at`.
- `ends_at`.
- `status`.
- `affected_services`.
- `public_notice`.
- `created_by`.
- `created_at`.
- `updated_at`.

## 18. Important database integrity constraints

Claude Code must explicitly implement and test the following:

1. One personal matrimonial profile per owner account.
2. One wallet per account.
3. One partner preference record per profile.
4. One profile privacy settings record per profile.
5. Unique normalized phone number.
6. Unique account email when supplied.
7. Unique favorite per user/profile.
8. Unique manager permission per authorization.
9. No duplicate active or pending manager authorization for the same profile/manager.
10. No duplicate active formal request between the same two profiles in either direction.
11. Sender and receiver must be different profiles.
12. No duplicate connection for an unordered profile pair.
13. One conversation per connection.
14. Exactly two active profile participants in an MVP conversation.
15. One read receipt per message/reader profile.
16. One ACTIVE document permission per document/recipient pair (G1, DCR-15).
17. *(Removed in G1, DCR-13: duplicate of item 2.)*
18. No negative credit balance.
19. Idempotency keys must be unique within their relevant operation scope.
20. Minimum age preference must not exceed maximum age.
21. Minimum earning must not exceed maximum earning.
22. Expiration timestamps must be later than start timestamps where required.
23. A manager cannot act through an inactive, expired, paused, or revoked authorization.
24. A private document cannot be accessed without a current permission.
25. A payment callback cannot create duplicate credits.
26. A request acceptance cannot create duplicate connections.
27. A deletion-processing step cannot be executed twice with harmful side effects.

## 19. Deletion strategy

Use deliberate `on_delete` policies.

Do not cascade-delete financial ledgers, audit history, moderation history, or legal-retention records merely because an account or profile is deleted.

Where appropriate:

- Retain legally required records.
- Anonymize personal identifiers.
- Revoke access permissions.
- Delete private media according to retention policy.
- Preserve legitimate conversation history for the other participant.
- Record the deletion operation and its result.

## 20. Indexing strategy

Add indexes based on common access patterns, including:

- User phone number and email.
- Profile owner and visibility/status.
- Profile location and search filters.
- Verification status and submission time.
- Active manager authorization by profile and manager.
- Request sender, receiver, status, and expiry.
- Request cooldown sender, receiver, and end time.
- Connection profile pair and status.
- Conversation connection and last message time.
- Message conversation and sent time.
- Document permission recipient and status.
- Credit transaction user and creation time.
- Payment gateway reference and status.
- Notification recipient and read status.
- Moderation case status and assigned moderator.
- Data export/deletion request status and creation time.
- Audit actor, resource, action, and timestamp.

Do not add every possible index without considering write overhead. Review query plans as real workloads become available.

## 21. Database implementation acceptance criteria

- All 16 module boundaries exist.
- All core models and relationships are implemented.
- Migrations apply cleanly to an empty database.
- Constraints prevent duplicate and invalid states.
- Critical financial operations use atomic transactions and locking.
- Sensitive fields and private media references are protected.
- Historical records are not silently overwritten.
- Tests cover all listed critical integrity constraints.
- Model relationships and deletion behavior are documented.

## 22. Reconciled database specification (G1)

**Applied corrections:** DCR-04, 05, 13, 14, 15, 19, 22, 23, 25, 27, 31, 35, 36, 37, 43, 44, 46, 47, 49, 51, 55, 56, 58, 60, 61, 62, 65, 67, 68, 69, 70, 71, 76, 77, 78, 79, 84, 85, 88, 89, 91, 93, 94, 95, 96, 97, 98, 99 (doc 20). G1 correction pass 2026-11-17 (DR-2026-11-17-C).

**Verbatim extracts** in this section start with a "*Verbatim from …*" line and end with "*— End of verbatim extract —*". Text outside those markers is editorial.

This section holds the database structures added or changed by the approved baseline (`docs/baseline/v4.6-F3/`). **Where it conflicts with §1–§21, this section wins.** In-place corrections in §2–§18 point here.

**Status of this content:** the structures are **[TR] PROPOSED** technical recommendations (doc 19, TR-01…TR-24) unless marked [DECIDED]. Rows marked [REC-BIZ] belong to an OPEN owner decision and are not implemented until that decision is recorded (`CLAUDE.md` CC-R25). Models land at the gate shown in doc 10 §0.

### 22.1 Source-of-truth register (DCR-05)

**Rule:** a derived value or projection has exactly one writer, can't be written through any serializer or admin form, and has a consistency test.

| # | Concept | Authoritative source | Derived / projection | Only writer | Consistency mechanism |
|---|---|---|---|---|---|
| 1 | Profile lifecycle | `MatrimonialProfile.profile_status` | None (`is_active` removed) | Profile transition service | State machine (doc 15) |
| 2 | Owner-chosen visibility | `MatrimonialProfile.visibility_status` | None (removed from privacy settings) | Privacy service | Single column |
| 3 | Effective access level (L0–L3) | Computed by the eligibility service | None | — | Computed per request |
| 4 | Identity status | Latest decided `IdentityVerification` cycle (doc 15 §3) | `MatrimonialProfile.identity_verified_at` | Verification service, same transaction | Same transaction + nightly check |
| 5 | Phone verified | `User.is_phone_verified` | — | OTP service; phone-change service clears it | Single writer |
| 6 | Display toggles | `ProfilePrivacySettings` | None (removed from data tables) | Privacy service | Single table |
| 7 | Photo moderation | `ProfilePhoto.moderation_status` | — | Moderation service | Single column |
| 8 | Credit history | Append-only ledger (`CreditOperation` + `CreditTransaction`). Permanent record. UPDATE/DELETE blocked by trigger. | — | Credit service (insert only) | Trigger + unique (account, idempotency key) |
| 9 | Credit balances | Ledger (Σ per bucket) | Projections: `CreditWallet.purchased_request_balance`, `CreditWallet.purchased_view_balance`; `CreditAllowance.remaining_amount` per allowance. Buckets stay separate [DECIDED]. | Credit service only, in the same transaction as the ledger row | Lock order wallet → allowances; `CHECK ≥ 0`, `CHECK remaining ≤ granted`; `bucket_balance_after` on every row; nightly reconciliation logs `ReconciliationDiscrepancy`, **no automatic fix**; corrections are compensating ADJUSTMENT operations under dual approval |
| 10 | Billing term | `SubscriptionBillingPeriod` rows | None (removed from `UserSubscription`) | Subscription service | Exclusion constraint against overlap |
| 11 | Messaging allowed | Connection status + blocks + restrictions | None (`Conversation.status` removed; doc 15 §8) | — | Eligibility check |
| 12 | Connection lifecycle | `ProfileConnection.status` (ACTIVE, PAUSED, COMPLETED, CLOSED) | None | Connection service | State machine (doc 15 §7) |
| 12a | Relationship progress stage | `RelationshipProgress.stage` (no CLOSED) | Displayed "Closed" label = connection CLOSED (computed, never stored) | Progress service | Writes need the connection ACTIVE |
| 13 | Time-bound validity | `expires_at` compared at runtime | `status` | Expiry jobs | Runtime check |
| 14 | Account usability | Reason records | `User.is_active` | Account-state service | Same transaction |
| 15 | Age | DOB | Never stored | — | Computed |
| 16 | Completion % | Field rules | `completion_percentage` | Profile service | Same transaction |
| 17 | Notification switches | Channel AND category; security bypasses | — | Preference service | Precedence function |
| 18 | View records | `ProfileView`: billing grant **and** security record of every grant | `VisitorHistory`: display projection only | View service | §22.6 |
| 19 | Sessions | `AuthSession` (state, kept after it ends) | — | Auth service | — |
| 19a | Security history | `AccountSecurityEvent` (append-only) | User "login and device history" view = selector | Auth, OTP and account-state services | Trigger blocks UPDATE/DELETE |
| 20 | Interest ↔ request link | `MatrimonialRequest.source_interest` | — | Request service | OneToOne |
| 21 | Interest and request liveness | `status` **and** `expires_at` together | `status` may lag until the worker or lazy expiry runs | Shared expiry function (doc 05) | Liveness predicate (§22.7) |
| 22 | Deletion overlay | `AccountDeletionRequest.status` | Not copied into the profile status | Deletion service | Computed in the eligibility service |
| 23 | Admin authorization | Active, unexpired `AdminUserRole` → `AdminRolePermission` | `User.is_staff` | Admin-role service | §22.15 |

### 22.2 Module 01 additions: sessions, security events, pseudonyms and keys

**`AuthSession`** [TR-01] replaces `LoginHistory` as the session record (DCR-25):
- `id`, `user`, `client_type` (WEB | MOBILE), `scope` (FULL | DELETION_RECOVERY), `status` (ACTIVE | REVOKED | EXPIRED)
- `created_at`, `last_seen_at`, `idle_expires_at`, `absolute_expires_at`, `reauthenticated_at`, `revoked_at`, `revoked_reason`
- `key_version_current` (mobile; the K_rot version used for the latest rotation)
- device and network metadata: `device_name`, `platform`, `app_version`, `user_agent`, `login_ip`, `last_ip`, `approximate_location`
- **No Django session key and no hash of one is stored.** The web link runs one way, from server-side session data (`auth_session_id`) to `AuthSession` (doc 06).
- Rows are retained after they end (retention per doc 13 OD-005). At deletion PROCESSING they are deleted unless a hold applies.

**`AuthToken`** (mobile) [TR-01]: `session`, `token_type` (ACCESS | REFRESH), `token_hash` (unique, SHA-256), `generation`, `parent_id`, `key_version`, `issued_at`, `expires_at`, `used_at`, `revoked_at`. Plaintext tokens are never stored.

**`AccountSecurityEvent`** [TR-17, TR-23] (replaces the field list in §2.2; append-only, UPDATE/DELETE blocked by trigger and privileges; monthly partitions, §22.15):
- plaintext event facts: `id` (UUIDv7), `event_type`, `result` (SUCCESS | FAILURE | INFO), `reason_code`, `actor_type` (SELF | ADMIN | SYSTEM | ANONYMOUS), `request_id`, `occurred_at`
- `subject_pseudonym`, `actor_pseudonym` (pseudonym UUIDs, never `user_id`)
- `subject_hash` (keyed HMAC of the normalised phone) only for events with no resolvable subject (for example a failed login for an unknown phone); 90-day retention
- `enc_parts`: per-subject encrypted envelopes holding the personal context (IP address, user agent, approximate location) and linkable identifiers such as `session_id` (§22.2 envelopes rule)
- event types: `LOGIN_SUCCEEDED`, `LOGIN_FAILED`, `LOGIN_DENIED_ACCOUNT_STATE`, `SESSION_CREATED`, `SESSION_REVOKED` (reasons LOGOUT, USER_REVOKED, USER_REVOKED_ALL, PASSWORD_RESET, PASSWORD_CHANGED, DEACTIVATED, DELETION_REQUESTED, ADMIN, REFRESH_REUSE, KEY_COMPROMISE), `REFRESH_REUSE_DETECTED`, `PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_COMPLETED`, `PASSWORD_RESET_FAILED`, `PASSWORD_CHANGED`, `PASSWORD_CHANGE_FAILED`, `OTP_VERIFICATION_FAILED`, `OTP_ATTEMPTS_EXHAUSTED`, `OTP_RATE_LIMITED`, `STEP_UP_SUCCEEDED`, `STEP_UP_FAILED`, `PHONE_CHANGED`, `EMAIL_CHANGED`, `ADMIN_MFA_ENROLLED`, `ADMIN_MFA_REMOVED`, `DEACTIVATED`, `REACTIVATED`, `DELETION_REQUESTED`, `DELETION_CANCELLED`, `SUSPICIOUS_ACTIVITY`, `RATE_LIMIT_TRIGGERED`
- flood control: while an IP or subject is throttled, one `RATE_LIMIT_TRIGGERED` per window instead of one row per rejected request
- access and retention rules: doc 06

**Pseudonyms and subject keys** [TR-23] (DCR-67, DCR-75, DCR-76, DCR-85):
- **`SubjectPseudonym`** (mutable mapping, restricted to the security admin role, reads audited): `pseudonym` (PK, random UUID), `subject_type` (ACCOUNT | PROFILE), `subject_id` (nullable), `created_at`, `unlinked_at`, `hold_ref` (nullable). One pseudonym per subject.
- **`SubjectDataKey`**: `key_id`, `pseudonym`, `kek_version`, `wrapped_key` (nullable), `created_at`, `destroyed_at`, with `CHECK ((destroyed_at IS NULL) = (wrapped_key IS NOT NULL))`. Destruction sets `wrapped_key = NULL` and `destroyed_at = now()`; the remaining row is a non-sensitive tombstone.
- **Eager creation:** the `SubjectPseudonym` and `SubjectDataKey` rows for an account or profile are created **in the same transaction that creates that account or profile**. Staff accounts are backfilled once at G4. Business transactions only read pseudonyms.
- **`ShreddedPseudonym`** (local cache of the external registry; primary key `pseudonym`): `subject_type`, `keys_digest`, `op_id`, `intent_seq`, `intent_entry_hash`, `shredded_at`. **No automatic expiry.** Re-apply is `INSERT … ON CONFLICT (pseudonym) DO NOTHING`; an existing row with a different `op_id` or `keys_digest` is an integrity alarm (doc 09).
- **`kek_rewrap_log`** (append-only): `key_id`, `from_version`, `to_version`, `rotate_op_id`, `rewrapped_at`, written by the KEK_ROTATE rewrap transaction (doc 09).

**Envelopes and linkable identifiers** (AuditLog and AccountSecurityEvent):
- Each personal value belongs to exactly one subject: request context (IP, user agent, location) belongs to the actor; values about a target belong to the target.
- Free-text personal content is banned in log rows; only reason codes and allowlisted structured fields.
- `enc_parts JSONB` holds an array of `{pseudonym, key_id, kek_version, nonce, ciphertext}`, one envelope per subject, encrypted with that subject's data key (AEAD, with the event ID and pseudonym as associated data); an insert trigger rejects duplicate pseudonyms.
- **Linkable-ID rule:** any identifier that could be joined to a retained record identifying a person (`session_id`, `authorization_id`, IDs of person-owned resources, ledger `account_id`) is stored only inside the owning subject's envelope; a resource belonging to two subjects goes into both envelopes. Plaintext is allowed for event facts, pseudonyms, `resource_type` and `request_id`.

**`IdempotencyRecord`** (G4) [TR-11]: stores, per account and `Idempotency-Key`, the request fingerprint and the original response so that a retry replays it. Exact columns are fixed at G4.

### 22.3 Module 02 additions

- `MatrimonialProfile.suspended_from_status` (ACTIVE | PAUSED), used to restore the prior state when a suspension is lifted (doc 15 §2).
- `ProfilePhoto`: add `uploaded_by`, `mime_type`, `size`, `checksum`, `width`, `height`, `processing_status` [TR-10].
- **`ProfileFieldCorrectionRequest`** [TR-06]: a request to correct an identity-locked field, reviewed by verification staff. Approval can trigger a new verification cycle (doc 15 §3). Which fields are locked is OD-04a (OPEN).

### 22.4 Module 04 additions

- `IdentityDocumentFingerprint`: add `key_version`.
- A restrictive identity hold during re-verification is a profile-level `UserRestriction(type = IDENTITY_REVIEW)` (§22.13). Re-verification rules are OD-04e [REC-BIZ, OPEN]; the cycle model is in doc 15 §3.

### 22.5 Module 05 additions

- `ProfileManagerAuthorization`: add `invitation_expires_at` and `invited_by`. Status transitions per doc 15 §4 (including PENDING → REVOKED when the owner cancels an invitation, PENDING → EXPIRED at the invitation TTL, and ACTIVE/PAUSED → REVOKED with reason RESIGNED; TTL and resignation are OD-05e/f, OPEN).
- `ManagerPermission`: replace `is_sensitive` with `tier` (N | S | H | O) per doc 14 [DCR-32; tiers OD-05, OPEN].
- **`maintenance_approval`** is in §22.15; it is unrelated to manager authorizations.

### 22.6 Module 06 additions: ProfileView and VisitorHistory (DCR-14, DCR-36, DCR-58)

- `ProfileView`: add `billing_account` (the owner of the represented profile performing the view). Its rows are written for every successful `POST /profiles/{id}/views/`, billable or not, and always store `viewer_user` (actual account), `viewer_profile`, `billing_account`, `target_profile`, `is_billable`, `credit_transaction`, `access_type`, `viewed_at`. **Private browsing never changes ProfileView.** Index `(billing_account, target_profile, viewed_at)` supports the 24-hour window check made under the wallet lock.
- `VisitorHistory` is a display projection. For a private visit it is written with `is_private_visit = true` and `visitor_profile` / `visitor_user` NULL; the identity stays only in ProfileView. Whether the owner sees an anonymous entry is OD-03g (OPEN). `VisitorHistoryRemoval` hides rows only and never touches ProfileView.
- Both are **insert-only** rows (lock level 8, doc 12 §5.3).
- `ProfileFavorite`: add `acting_profile`, with uniqueness on (`user`, `acting_profile`, `profile`).

### 22.7 Module 07: interests, cooldowns and requests

**`Interest`** [TR; behaviours OD-06, OPEN] (DCR-04, DCR-51):
- `id`, `sender_profile` (PROTECT), `receiver_profile` (PROTECT)
- `status`: PENDING | RECIPROCATED | CONVERTED_TO_REQUEST | DECLINED | WITHDRAWN | EXPIRED | CLOSED
- `sent_at`, `responded_at`, `expires_at` (set once at creation: `sent_at + configured period` if OD-06e is approved, otherwise NULL; immutable), `closed_at`, `closure_reason` (BLOCKED | PROFILE_CLOSED | ACCOUNT_DELETED | ADMIN; `SUPERSEDED_BY_REQUEST` removed)
- `created_by`, `updated_by` (actual accounts)
- `CHECK (sender_profile_id <> receiver_profile_id)`; partial unique on `(LEAST(sender, receiver), GREATEST(sender, receiver)) WHERE status IN ('PENDING','RECIPROCATED')`
- **Liveness predicate:** `(status = 'PENDING' AND (expires_at IS NULL OR expires_at > now)) OR status = 'RECIPROCATED'`. Expiry applies only to PENDING.

**`InterestHistory`**: append-only transition history.

**`DirectionalCooldown`** replaces `RequestCooldown` (§8.3): `sender_profile`, `receiver_profile`, `source_type` (INTEREST | REQUEST), `source_id` (unique), `reason`, `starts_at`, `ends_at`, `created_at`. A request expiry cooldown starts at the request's logical expiry time, not when the worker runs. Cooldowns are directional [DECIDED]; whether one blocks both interests and requests is OD-06g (OPEN).

**`MatrimonialRequest`** additions:
- `source_interest`: OneToOne to `Interest`, nullable, PROTECT, `related_name="formal_request"` (DCR-27). There is no FK from Interest to the request; one interest can never produce two requests.
- `debit_operation_id`: FK to `CreditOperation`, with `UNIQUE (id, debit_operation_id)` (refund integrity, §22.11).
- Cancellation fields (DCR-46): `cancellation_reason`, `cancelled_by_type` (ADMIN | SYSTEM), `cancelled_by` (admin account, nullable), `cancellation_ref_type`, `cancellation_ref_id`, with `CHECK ((status = 'CANCELLED') = (cancellation_reason IS NOT NULL))`. **No refund-outcome column**: the outcome is derived from the request's `CreditRefundOperation` lines. Trigger list and reason codes: doc 05 §25.2 [REC-BIZ, OD-07, OPEN]. Only the administrative cancellation itself (T1/T2: CANCELLED with an authorized actor and a reason, no cooldown) is DECIDED. Whether any trigger refunds, **including the T2 refund**, is OD-07b (OPEN).
- Partial unique on the normalised pair `WHERE status = 'PENDING'` (duplicate active requests in either direction prohibited [DECIDED]).

### 22.8 Module 08: connections and progress (DCR-37, DCR-47, DCR-48, DCR-49, DCR-55)

`ProfileConnection` additions:
- `paused_by_profile` (FK to `MatrimonialProfile`, PROTECT, nullable): the **party** is the profile; `paused_at`; `pause_reason` (optional). The acting account is recorded only in `ConnectionHistory`.
- `closed_from_status` (ACTIVE | PAUSED | COMPLETED). Reopening requires `closed_from_status <> 'COMPLETED'` [OD-06l, OPEN].

Pause-state constraint (DCR-55):

```sql
CONSTRAINT connection_pause_state_consistent CHECK (
  (status = 'PAUSED'
     AND paused_by_profile_id IS NOT NULL
     AND paused_at IS NOT NULL
     AND paused_by_profile_id IN (profile_one_id, profile_two_id))
  OR
  (status <> 'PAUSED'
     AND paused_by_profile_id IS NULL
     AND paused_at IS NULL
     AND pause_reason IS NULL)
)
```

- `status`, `profile_one_id` and `profile_two_id` are `NOT NULL`, so the `IN` comparison can never evaluate to NULL.
- `pause_reason` is optional while paused and must be NULL otherwise.
- Every exit from PAUSED (resume, close, complete) clears all three fields in the same UPDATE.

`RelationshipProgress.status` is renamed **`stage`**. Allowed values: REQUEST_ACCEPTED, INITIAL_COMMUNICATION, DISCUSSION_IN_PROGRESS, MEETING_PLANNED, MEETING_COMPLETED, PROPOSAL_SERIOUS_DISCUSSION, ENGAGED. **`CLOSED` is removed from the stored values**; the "Closed" label shown to users is derived from `ProfileConnection.status = CLOSED` (FR-CON-004 list preserved; storage change is OD-06i, OPEN). `RelationshipProgressHistory` uses `previous_stage` / `new_stage`.

**`ConnectionReopenRequest`** [TR; rules OD-06n, OPEN]: `connection`, `initiated_by_profile`, `initiated_by_account`, `status` (PENDING | CONFIRMED | DECLINED | WITHDRAWN | EXPIRED | INVALIDATED), `invalidation_reason`, `expires_at`, `created_at`, `responded_at`. Partial unique: one PENDING request per connection.

### 22.9 Module 09 changes

- `Conversation.status` is removed. Conversation state is derived from the connection and blocks (doc 15 §8).
- `DocumentAccessPermission`: the unique constraint on document + recipient profile becomes a **partial unique `WHERE status = 'ACTIVE'`**, so a new permission can be issued after expiry or revocation (DCR-15).

### 22.10 Module 10 changes

- `PhotoAccessPermission`: partial unique on (`owner_profile`, `recipient_profile`) `WHERE status = 'ACTIVE'` (DCR-15).
- `VisitorHistory` and `VisitorHistoryRemoval`: see §22.6.

### 22.11 Module 11: ledger, refunds, wallet and reconciliation

**Projections** (§22.1 rows 8–9): `CreditWallet` keeps only the purchased buckets (`purchased_request_balance`, `purchased_view_balance`). Subscription allowances are tracked per `CreditAllowance`. Every ledger row records `bucket_balance_after`.

**Ledger and refund structures** (DCR-56, DCR-65, DCR-70):

> *Verbatim from `docs/baseline/v4.6-F3/approved/05_v4.4.md` §3.1–3.3. Section references inside this block refer to that package.*

##### 3.1 Columns and unique keys [TR]

**`CreditOperation`:**
- `id` (PK), `account_id`, `kind` (DEBIT | GRANT | PURCHASE | EXPIRY | REFUND | ADJUSTMENT | DISPOSITION), `idempotency_key`
- **`UNIQUE (id, account_id, kind)`** (FK target **UK-OP**)
- `UNIQUE (account_id, idempotency_key)`

**`CreditTransaction`:**
- `id` (PK), `account_id`, `operation_id`, `operation_kind`
- `bucket`, `allowance_id` (nullable)
- `amount` (> 0), `direction` (DEBIT | CREDIT), `entry_type` (USAGE | GRANT | PURCHASE | EXPIRY | REFUND | ADJUSTMENT | DISPOSITION)
- `refund_operation_id` (nullable), `bucket_balance_after`
- **FK (operation_id, account_id, operation_kind) → CreditOperation (id, account_id, kind)** [UK-OP]
- **`UNIQUE (id, account_id, operation_id, bucket, amount, direction, entry_type)`** (FK target **UK-CT**)
- CHECKs:
  - `entry_type='USAGE' ⇒ direction='DEBIT' AND operation_kind='DEBIT'`
  - `entry_type='REFUND' ⇒ direction='CREDIT' AND operation_kind='REFUND' AND refund_operation_id IS NOT NULL`
  - `(bucket LIKE 'ALLOWANCE_%') = (allowance_id IS NOT NULL)`

**`CreditRefundOperation`:**
- `id`, `account_id`, `source_type`, `request_id`
- `original_operation_id`, `original_kind` (CHECK `= 'DEBIT'`)
- `refund_credit_operation_id`, `refund_kind` (CHECK `= 'REFUND'`)
- **FK (original_operation_id, account_id, original_kind) → CreditOperation (id, account_id, kind)** [UK-OP]
- **FK (refund_credit_operation_id, account_id, refund_kind) → CreditOperation (id, account_id, kind)** [UK-OP]. This puts "the refund operation's kind is REFUND" in a database FK. In v4.3 it was a trigger.
- **FK (request_id, original_operation_id) → MatrimonialRequest (id, debit_operation_id)** (requires `UNIQUE (id, debit_operation_id)` on the request)
- `UNIQUE (source_type, request_id)`
- `UNIQUE (refund_credit_operation_id)`
- **`UNIQUE (id, account_id, original_operation_id)`** (target **UK-RO1**)
- **`UNIQUE (id, refund_credit_operation_id)`** (target **UK-RO2**)

**`CreditRefundLine`** (all ordinary columns):

| Column group | Columns | Nullability |
|---|---|---|
| Parent | `refund_operation_id`, `account_id`, `original_operation_id` | Always NOT NULL |
| Original debit | `original_transaction_id`, `original_bucket`, `original_amount`, `original_direction` (CHECK `'DEBIT'`), `original_entry_type` (CHECK `'USAGE'`) | Always NOT NULL |
| Disposition | `disposition` (REFUNDED \| LAPSED) | NOT NULL |
| Refund side | `refund_transaction_id`, `refund_account_id`, `refund_credit_operation_id`, `refund_bucket`, `refund_amount`, `refund_direction`, `refund_entry_type` | **All NULL** when LAPSED, **all NOT NULL** when REFUNDED |

##### 3.2 Matching foreign keys

Each FK's column list matches its target unique key exactly, column for column.

| FK | Referencing columns (CreditRefundLine) | Target | Match | Purpose |
|---|---|---|---|---|
| FK-L1 | (original_transaction_id, account_id, original_operation_id, original_bucket, original_amount, original_direction, original_entry_type) | CreditTransaction **UK-CT** (id, account_id, operation_id, bucket, amount, direction, entry_type) | FULL (all NOT NULL) | The original is a USAGE debit, of this account, in this operation, in this bucket, for this amount |
| FK-L2 | (refund_transaction_id, refund_account_id, refund_credit_operation_id, refund_bucket, refund_amount, refund_direction, refund_entry_type) | CreditTransaction **UK-CT** | **FULL**: all NULL (LAPSED) or all checked (REFUNDED). A partly filled row is rejected. | The refund row is a CREDIT/REFUND in the refund operation, with matching account, bucket and amount |
| FK-L3 | (refund_operation_id, account_id, original_operation_id) | CreditRefundOperation **UK-RO1** | FULL | The line belongs to a parent with the same account and original operation |
| FK-L4 | (refund_operation_id, refund_credit_operation_id) | CreditRefundOperation **UK-RO2** | SIMPLE (skipped only when `refund_credit_operation_id` is NULL, which a CHECK allows only for LAPSED) | The refund row's operation is the parent's REFUND operation |

**CHECKs on the line:**
- `disposition='LAPSED' ⇒` all seven refund-side columns are NULL.
- `disposition='REFUNDED' ⇒` all seven are NOT NULL **and** `refund_account_id = account_id`, `refund_bucket = original_bucket`, `refund_amount = original_amount`, `refund_direction = 'CREDIT'`, `refund_entry_type = 'REFUND'`.
- `UNIQUE (original_transaction_id)`, `UNIQUE (refund_transaction_id)`.

**How the chain proves the refund row belongs to a REFUND operation with direction CREDIT:**
1. FK-L2 forces the refund transaction to have `entry_type = 'REFUND'`, `direction = 'CREDIT'`, and `operation_id = refund_credit_operation_id`.
2. The CreditTransaction CHECK forces `operation_kind = 'REFUND'`, and its FK to UK-OP makes that kind real.
3. FK-L4 and the parent's FK to UK-OP tie that operation to the parent's REFUND operation.

All of this is enforced by database constraints.

##### 3.3 Where each rule is enforced

| Layer | Rules |
|---|---|
| **Database constraints** (unique, FK, CHECK) | Account equality. Original-operation equality. Bucket equality. Amount equality (stricter than ≤). Debit is USAGE/DEBIT. Refund is CREDIT/REFUND in a REFUND-kind operation. Each debit row refunded at most once. Each refund row used once. One refund per request. Request ↔ debit operation link. All-or-nothing refund-side columns. |
| **Triggers** | (a) `BEFORE INSERT` on the line: original and refund `allowance_id` must be equal (`IS NOT DISTINCT FROM`). This can't be a composite FK because `allowance_id` is NULL for purchased buckets. (b) `DEFERRABLE INITIALLY DEFERRED` at commit: line count = number of the original operation's USAGE rows. Every REFUND CreditOperation has exactly one CreditRefundOperation. (c) `BEFORE UPDATE OR DELETE` rejects every change on CreditOperation, CreditTransaction, CreditRefundOperation and CreditRefundLine. |
| **Service validation, transactional** | Whether the cancellation reason qualifies for a refund (OD-07). The lapse decision (allowance EXPIRED, read under the allowance lock). Lock order. Projection update. Building lines from the full debit set. Outbox lease handling. |
| **Nightly reconciliation** | Projection = Σ ledger. Every qualifying CANCELLED request has a refund operation. Post-closure credits (§4). |

**Tests:** T-REQ-039…046 rewritten against FK-L1…L4 and the CHECKs, including a partly filled refund side rejected by MATCH FULL, a refund row in a non-REFUND operation rejected, and wrong direction or entry type rejected. Plus T-REQ-050 (allowance-mismatch trigger) and T-REQ-051 (deferred one-parent-per-REFUND-operation trigger).

*— End of verbatim extract —*

---


**Refund operation key** (DCR-69): the refund `CreditOperation` uses `idempotency_key = 'refund:request:<request_id>'` under `UNIQUE (account_id, idempotency_key)`. The refund workflow is in doc 05.

**Wallet closure and disposition** (DCR-71, DCR-78) [mechanics TR; final treatment OD-07g, OPEN]:
- `CreditWallet` gains `status` (ACTIVE | CLOSED_RETAINED | DISPOSED) and `closed_at`.
- Wallet CHECKs are only `purchased_* ≥ 0`. There is deliberately **no** CHECK tying DISPOSED to a zero balance.
- A trigger on non-ACTIVE wallets rejects new rows with `entry_type IN ('USAGE','GRANT','PURCHASE')`, and allows `REFUND` credits and `DISPOSITION` / `ADJUSTMENT` operations.
- `CreditTransaction` CHECK: `entry_type = 'DISPOSITION' ⇒ operation_kind = 'DISPOSITION' AND direction = 'DEBIT'`.
- Refund rows recorded after closure carry `post_closure = true` (set at insert, never updated).
- **DISPOSED can't be reached until OD-07g is approved.**

**`ReconciliationDiscrepancy`**: `id`, `type` (for example PROJECTION_MISMATCH, REFUND_INTEGRITY, POST_DISPOSITION_CREDIT, FINANCIAL_EVENT_UNDECRYPTABLE), `status` (OPEN | RESOLVED), subject references, details, `created_at`, `resolved_at`; for `FINANCIAL_EVENT_UNDECRYPTABLE` also `outbox_event_id`, `replacement_event_id`, `last_check_at`, `last_check_result` (AWAITING_REPLACEMENT | REPLACEMENT_PENDING | REPLACEMENT_FAILED | VERIFIED). Rows are locked only by reconciliation transactions (doc 12 §5.3).

**`UserSubscription`**: add an `is_paid` snapshot used by the partial unique index. The `PAYMENT_FAILED` status stays in the schema but is **dormant** while renewal is manual (FR-SUB-008 implementation DEFERRED under OD-09a, OPEN).

### 22.12 Module 12: OutboxEvent (replaces §13.10 NotificationOutbox) — DCR-22, 68, 73, 84, 98

**Approved core vs proposed refinements (DR-2026-11-17-C2):** the core requirement is APPROVED (SRS FR-NOT-005; ADR-014 core): an outbox record written in the same transaction as the business operation and processed asynchronously with retryable, idempotent delivery. **Everything else in this section is [TR-11] PROPOSED** (ADR-028): its location, columns, statuses, classes, keys, redaction and retention. DCR-62 (post-commit refund obligation through the outbox) and DCR-89 (`category` and notification eligibility through `can_notify`, doc 05 §25.5) are applied here.

`OutboxEvent` lives in `common/events` [TR-11]. It is a **mutable work queue**, not an append-only log.

| Column | Content | Plaintext? |
|---|---|---|
| `id` (UUIDv7), `event_type`, `event_class` (NOTIFICATION \| FINANCIAL_OBLIGATION), `category` (SECURITY \| FINANCIAL \| MATRIMONIAL_ACTIVITY \| ACCOUNT \| SYSTEM), `status`, `attempts`, `lease_token`, `lease_expires_at`, `created_at` | Queue facts | Yes |
| `recipient_pseudonym` | The recipient account's `SubjectPseudonym`; NULL for system events | Yes (random UUID) |
| `dedupe_key` | `HMAC-SHA256(K_dedupe, business event identity)` | Yes (not reversible) |
| `aggregate_type` | For example `MatrimonialRequest` | Yes |
| `payload_enc`, `queue_key_version` | Aggregate ID and handler parameters, encrypted with the queue key `K_queue[v]` (AEAD, `id` as associated data) | No |
| `obligation_resolution` (PENDING \| REPLACED_VERIFIED \| OBLIGATION_SATISFIED_VERIFIED), `replaced_by_event_id`, `resolved_at` | FINANCIAL_OBLIGATION events only | Yes |

- **Statuses:** PENDING, CLAIMED, DONE, CANCELLED, DEAD, BLOCKED_INTEGRITY, DEAD_UNDECRYPTABLE.
- **Banned in the row:** raw user, profile or resource IDs; names; phone numbers; message text.
- **Dedupe:** `UNIQUE (dedupe_key) WHERE status NOT IN ('DEAD_UNDECRYPTABLE','CANCELLED')`.
- **Redaction trigger:** `payload_enc`, `recipient_pseudonym` and `dedupe_key` may only change from a value to NULL, and only on a terminal row (DONE, CANCELLED, DEAD, DEAD_UNDECRYPTABLE). For FINANCIAL_OBLIGATION rows, redaction additionally requires: `DONE` with the refund verified and 7 days passed; or `DEAD_UNDECRYPTABLE` with `obligation_resolution` resolved and `resolved_at + 7 days ≤ now`; or `DEAD` resolved by an operator intervention. An unresolved `DEAD_UNDECRYPTABLE` row is never redacted or purged.
- **Retention:** redacted 7 days after the terminal condition above; purged at 30 days.
- **Queue key:** each version is wrapped by the KEK and rotated monthly; destruction preconditions are in doc 09.
- Processing (two-phase claim and completion), deletion behaviour and the financial-obligation lifecycle are in doc 12 §6 and doc 05.

### 22.13 Module 13 additions

- `UserRestriction` types used by the eligibility service include account-level `LOGIN` and `FULL_ACCOUNT` and profile-level `IDENTITY_REVIEW` (re-verification hold) [TR-03].
- **`restore_quarantine`** (DCR-93): subjects whose Stream R deletion couldn't be re-applied after a restore. `get_account_standing` treats a quarantined subject as `RESTORE_QUARANTINED`, handled exactly like `DELETION_PROCESSING` (doc 06, doc 09).

### 22.14 Module 14 additions

- `AccountDeletionRequest`: partial unique index allowing **one non-terminal deletion request per user**, `WHERE status IN ('REQUESTED','IDENTITY_VERIFICATION_REQUIRED','PENDING_RECOVERY','PROCESSING')` (DCR-61). It links to its Stream R operation; the transition to PROCESSING requires that operation to be `INTENT_REGISTERED` or later (CHECK + service rule, doc 09). Reason value `RESTORE_REAPPLY` is used only by the restore path.

### 22.15 Module 15 additions: logs, partitions, maintenance and admin authorization

**Admin authorization (DCR-44)** [TR-07]: the single source of administrative authorization is §16.2–16.5 (`AdminRole`, `AdminPermission`, `AdminRolePermission`, `AdminUserRole` with `assigned_by`, `assigned_at`, `expires_at`, `revoked_at`). A custom Django authentication backend reads these tables. **Django Groups and `user_permissions` are not used** and their admin pages are hidden. `User.is_staff` is a projection written only by the admin-role service. `is_superuser` is break-glass only (at most two accounts, audited, MFA). The `AdminRoleAssignment` name proposed earlier is not used; `AdminUserRole` is the assignment table.

**`AuditLog`** (replaces the reference style in §16.1; DCR-60, DCR-67, DCR-76): append-only (trigger plus privileges); monthly partitions; actor, subject and represented-profile references stored as **pseudonyms**, personal context and linkable IDs inside `enc_parts`, as for AccountSecurityEvent (§22.2). No database foreign keys on these columns.

**UUIDv7 IDs and partitions (DCR-79, DCR-88):**

> *Verbatim from `docs/baseline/v4.6-F3/approved/07_v4.6.md` §4.1–4.3. Section references inside this block refer to that package.*

##### 4.1 Version-specific generation (C-56)

- **PostgreSQL 18:** use the built-in **`uuidv7()`**.
- **PostgreSQL 15/16:** use the custom implementation below. It's RFC 9562 layout: 48-bit Unix millisecond timestamp, version 7, 12-bit `rand_a`, variant `10`, 62-bit `rand_b`. It needs no extension, because `gen_random_uuid()` is built in from PostgreSQL 13.
- **Portable column default:** every table uses `uuid_v7()`. A migration creates `uuid_v7()` as a wrapper around `uuidv7()` when `server_version_num ≥ 180000`, and as the custom body otherwise.

```sql
CREATE OR REPLACE FUNCTION uuid_v7() RETURNS uuid
LANGUAGE plpgsql VOLATILE PARALLEL SAFE AS $$
DECLARE
  ts_ms bigint := floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint;
  b     bytea  := uuid_send(gen_random_uuid());          -- 16 random-ish bytes (v4)
BEGIN
  b := overlay(b PLACING substring(int8send(ts_ms) FROM 3 FOR 6) FROM 1 FOR 6); -- 48-bit ts, big-endian
  b := set_byte(b, 6, (get_byte(b, 6) & 15)  | 112);    -- version nibble 0111
  b := set_byte(b, 8, (get_byte(b, 8) & 63)  | 128);    -- variant bits 10
  RETURN encode(b, 'hex')::uuid;
END $$;
```

That leaves 74 random bits (12 in `rand_a`, 62 in `rand_b`). Uniqueness is enforced by the primary key, not assumed.

##### 4.2 `uuid_v7_lower(ts)`

This returns the **smallest valid UUIDv7 for the millisecond containing `ts`**: timestamp bytes, version nibble 7, every random bit zero, variant `10`.

```sql
CREATE OR REPLACE FUNCTION uuid_v7_lower(ts timestamptz) RETURNS uuid
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
  SELECT encode(
           substring(int8send(floor(extract(epoch FROM ts) * 1000)::bigint) FROM 3 FOR 6)
           || '\x70008000000000000000'::bytea,          -- 70 00 | 80 00 00 00 00 00 00 00
         'hex')::uuid
$$;
```

**Why the boundaries are correct:** PostgreSQL compares UUIDs byte by byte, unsigned, and the timestamp is in the most significant 6 bytes. So:
- every v7 UUID with timestamp ≥ T sorts ≥ `uuid_v7_lower(T)`, because with an equal timestamp, byte 6 is `0x7?` ≥ `0x70`, byte 7 ≥ `0x00`, and byte 8 is in `0x80–0xBF`, which is ≥ `0x80`
- every v7 UUID with timestamp < T sorts below it

`extract(epoch FROM timestamptz)` doesn't depend on the session timezone, so `IMMUTABLE` holds. Boundaries are always written as UTC literals.

##### 4.3 Partitions

```sql
CREATE TABLE audit_log (..., id uuid NOT NULL DEFAULT uuid_v7(), ...,
  CONSTRAINT audit_log_id_is_v7 CHECK (
     substring(id::text, 15, 1) = '7' AND substring(id::text, 20, 1) IN ('8','9','a','b')),
  PRIMARY KEY (id)) PARTITION BY RANGE (id);

CREATE TABLE audit_log_2027_01 PARTITION OF audit_log
  FOR VALUES FROM (uuid_v7_lower('2027-01-01 00:00:00+00'))
             TO   (uuid_v7_lower('2027-02-01 00:00:00+00'));   -- TO is exclusive
```

- No DEFAULT partition. Partitions are created 3 months ahead (v4.5).
- The CHECK rejects non-v7 UUIDs, which could otherwise be routed to the wrong partition.
- **CI runs on PostgreSQL 16 and 18**, covering both code paths. AS-3 is unchanged (≥ 15 supported).

*— End of verbatim extract —*


`account_security_event` is partitioned the same way.

**Held events (hold table)** [TR-23]:
- `audit_log_hold`: unpartitioned, same columns, `PRIMARY KEY (id)`. `audit_log_hold_link (event_id, hold_case_id)`, `PRIMARY KEY (event_id, hold_case_id)`.
- Moving held events and dropping a partition happen in one transaction (copy with `ON CONFLICT DO NOTHING`, plain DETACH, DROP, maintenance record). Past ranges are never re-created (except the restore exception in doc 09). Reads use the view `audit_log_all` (UNION ALL of both tables).
- Release: the security-definer function `release_held_events(hold_case_id)`, callable only by the maintenance role, removes links for the hold and deletes only rows that have no remaining link, whose pseudonyms are under no other active hold, and whose retention has passed (stricter of intent-time and apply-time values). Rows failing the retention check stay with `retain_until` and are removed later by `HOLD_RETENTION_PURGE` (doc 09). The application role can't update or delete either table.

**Maintenance tables** [TR-24] (separate lock domain; doc 09 holds the protocol):
- **`maintenance_audit_log`**: append-only, partitioned yearly by UUIDv7 `id`, no personal data. One row per registry entry. Its columns are the registry entry header fields plus `entry_hash` and `restored_from_registry` (definition below).
- **`maintenance_operation`** (mutable state): `op_id` (UUIDv7 PK), `stream` (R | M), `kind`, `target_digest`, `status` (per the stream state machines in doc 09), `intent_seq`, `intent_hash`, `outcome_seq`, `outcome_hash`, `attempts`, `last_error`, timestamps; `UNIQUE (kind, target_digest) WHERE status <> 'ABORTED'`; a CHECK rejects `ABORTED` for Stream R.
- **`registry_stream_head`**: `(stream PK, last_seq, last_hash, pending_op_id NULL)`.
- **`maintenance_approval`**: `(op_id, approver_user_id, approved_at, permission_code)`, `PRIMARY KEY (op_id, approver_user_id)`, with a trigger rejecting the requester as an approver.

Registry entry and local log row definition (DCR-95):

> *Verbatim from `docs/baseline/v4.6-F3/approved/09_v4.6-F1.md` Correction 1. Section references inside this block refer to that package.*

> **A.1 Registry entry structure.** Every registry entry has four parts: `header`, `params`, `entry_hash` and `signature`.
>
> **Header** (non-derived, no personal data). One registry entry corresponds to **exactly one** `maintenance_audit_log` row. The header *is* that row's recoverable content:
> `schema_version`, `stream`, `seq`, `prev_hash`, `registry_key_version`, `op_id`, `parent_op_id`, `kind`, `phase`, `log_row_id` (UUIDv7, generated before seq allocation), `target_digest`, `params_digest`, `companion_ref` (`{key, sha256, count}` or null), `summary` (an operational object: table, partition name, range bounds, counts, digests; **never pseudonyms**), `executor_job_run_id`, `executor_role`, `requested_by_pseudonym`, `approvals` (array, Correction 5), `recorded_at`.
>
> **Params:** the kind-specific recoverable parameters (A.3, Correction 3). Bound to the header by `params_digest = SHA-256(JCS(params))`.
>
> **Canonical hash input:** `H_in = "MATREG" ‖ 0x00 ‖ "v1" ‖ 0x00 ‖ JCS(header)`, where JCS is the RFC 8785 JSON Canonicalization Scheme in UTF-8. Encoding rules:
> - UUIDs: lowercase.
> - Timestamps: RFC 3339 UTC with milliseconds and a `Z`.
> - Digests: lowercase hex.
> - Integers: JSON numbers below 2^53, otherwise decimal strings.
> - Absent optional fields: explicit `null`.
>
> **Hash and signature:** `entry_hash = SHA-256(H_in)` and `signature = HMAC-SHA256(K_reg[registry_key_version], entry_hash)`.
>
> `entry_hash` and `signature` are **not** part of `H_in`. `seq` and `prev_hash` **are** part of it, which is what links the chain. So there's no circular dependency.
>
> **Local log row:** `maintenance_audit_log` columns = every header field, plus `entry_hash` and `restored_from_registry`. `params` aren't stored locally, which keeps Stream R pseudonyms out of the long-lived local log.
>
> **Reconstruction procedure:**
> 1. Fetch the entry.
> 2. Verify `signature` over `entry_hash`.
> 3. Recompute `SHA-256(H_in)` from the header and require it to equal `entry_hash`.
> 4. Require `prev_hash` = the previous entry's `entry_hash`, and `seq` = previous `seq` + 1.
> 5. Recompute `params_digest` and require a match.
> 6. Insert the local row from the header fields, with `seq`, `prev_hash` and `entry_hash` copied from the verified entry, using `ON CONFLICT (id) DO NOTHING` and `restored_from_registry = true`.
>
> **Local verification:** from local columns alone, rebuild the header, recompute `entry_hash`, and check the chain across rows ordered by (`stream`, `seq`).

*— End of verbatim extract —*


### 22.16 Items removed or renamed

| Item | Change | DCR |
|---|---|---|
| §2.3 `LoginHistory` | Retired; replaced by `AuthSession` + `AccountSecurityEvent` | DCR-25 |
| §8.3 `RequestCooldown` | Generalised into `DirectionalCooldown` | DCR-19 |
| §9.3 `RelationshipProgress.status` | Renamed `stage`; `CLOSED` removed from stored values | DCR-37 |
| §10.1 `Conversation.status` | Removed (derived) | DCR-05 |
| §13.3 `security_notifications_enabled` | Removed | DCR-23 |
| §13.10 `NotificationOutbox` | Replaced by `OutboxEvent` (§22.12) | DCR-22, DCR-68 |
| §18 duplicated "one wallet" item | Removed | DCR-13 |
| `MatrimonialRequest.refund_outcome` (proposed in v4.1) | Never added; outcome derived | DCR-56 |
| `Interest.closure_reason = SUPERSEDED_BY_REQUEST` | Never added | DCR-51 |

### 22.17 G4 implementation record (2026-11-18, DR-2026-11-18-G4)

Editorial record of how G4 implemented §22 (the TRs above were approved by DR-2026-11-18-G4-10). Where §22 left a detail open, the choice below was made under the clarification policy of DR-2026-11-18-G4 and is the current design.

| Item | Implementation |
|---|---|
| App placement | `accounts`: User, AuthSession, AuthToken, AccountSecurityEvent, SubjectPseudonym, SubjectDataKey. `audit`: AuditLog, `audit_log_hold`, `audit_log_hold_link`, view `audit_log_all`. `common/events`: OutboxEvent. `common/idempotency`: IdempotencyRecord. `platform_ops`: TR-24 tables, `shredded_pseudonym`, `kek_rewrap_log` |
| Migrations | One initial migration per app. Project-wide SQL functions (`uuid_v7`, `uuid_v7_lower`, `ensure_uuid7_partitions`, `reject_row_change`, `check_enc_parts`) live in `accounts.0001`, the root migration. Every RunSQL has reverse SQL; all migrations reverse to zero on PostgreSQL 16 and 18 |
| **IdempotencyRecord** (columns fixed at G4) | `id`, `account` (FK, PROTECT), `key` (8–128 chars `[A-Za-z0-9_.:-]`), `scope` (operation code), `request_fingerprint` (SHA-256 of method, path and canonical body), `status` (COMPLETED), `response_status`, `response_body`, `created_at`, `expires_at` (default 24 h; purged). `UNIQUE (account, key)`. Written in the operation's own transaction; a different scope or body for the same key is a conflict, never a replay |
| **AuditLog** columns | `actor_type` USER / MANAGER / ADMIN / SYSTEM; `actor_pseudonym`, `subject_pseudonym`, `represented_profile_pseudonym`; `action` and `resource_type` as dotted lowercase codes (CHECK); `result` SUCCESS / FAILURE / DENIED; `category` SYSTEM / FINANCIAL / ADMINISTRATIVE / STATE_CHANGE / SECURITY (retention per category); `request_id`; `safe_metadata` (allowlist: snake_case keys, scalar values, code-like strings only); `enc_parts`. Hold rows add `retain_until` and `moved_at` |
| Hold tables | Held-event tables exist for `audit_log` only, as specified; security-event retention is partition-level |
| OutboxEvent additions | `terminal_at` and `redacted_at` (needed to apply the 7/30-day rules); `obligation_resolution` is set to PENDING for FINANCIAL_OBLIGATION events at emit |
| Partitions | Created 3 months (logs) / 1 year (maintenance log) ahead. The first partitions are created by the migrations, before the registry exists; every later partition change is a recorded PARTITION_CREATE / PARTITION_DROP operation |
| `registry_stream_head` | Natural key `stream` (the only non-UUID primary key; a two-row control table) |
| Database roles (D-11) | Append-only enforced by triggers for every role; the application-role GRANT model is `common/db/grants.py` (tested); applying it to deployed roles is deployment work |

### 22.18 G5 Phase 2 implementation record (2026-11-19, DR-2026-11-18-G4)

Editorial record of the schema added in G5 Phase 2 (authentication and admin access). It adds no requirement. Choices were made under the DR-2026-11-18-G4 clarification policy; the admin MFA choices are in ADR-033.

| Item | Implementation |
|---|---|
| `verification.PhoneVerification` (Phase 2a) | §2.5 / §5.1: code stored only as HMAC (OTP key ring); one pending code per phone and purpose; state and E.164 CHECKs |
| `AuthSession.client_type` (`accounts.0002`) | Adds `ADMIN`: the separate Django Admin session (doc 06 §22.2; 30 min idle, 12 h absolute). The API accepts only `WEB` (session) and `MOBILE` (bearer) sessions |
| **`admin_role`, `admin_permission`, `admin_role_permission`, `admin_user_role`** (`admin_access.0001`) | §16.2–16.5 fields. Additions: code CHECKs; `admin_user_role.assigned_by` nullable for CLI-operator assignments (the audit log records `channel=cli`); partial unique index `(user, role) WHERE revoked_at IS NULL`; CHECKs: expiry after assignment, revocation after assignment, `user <> assigned_by`. Rows are never deleted; roles and permissions are retired (`is_active = false`). All FKs `PROTECT` |
| **`admin_totp_device`** | django-otp device. **Integer primary key** (library-imposed, ADR-033 §3). One per account (`user` unique, `PROTECT`). Seed stored only as AES-256-GCM ciphertext (`key_version`, `key_nonce`, `key_ciphertext`; ADMIN_MFA key ring). Also `digits` (6/8), `step` (≥ 15), `tolerance` (≤ 2), `drift`, `last_t` (replay), throttling and timestamp columns |
| **`admin_mfa_enrollment`** | Single-use enrollment code: `code_hash` (HMAC, unique), `issued_by` (nullable for the CLI), `created_at`, `expires_at`, `used_at`, `revoked_at`. CHECKs: hash format, expiry after creation, not both used and revoked, not self-issued; at most one open code per account (partial unique index) |
| **Superuser limit** | Trigger `admin_superuser_limit` on `accounts_user` (`BEFORE INSERT OR UPDATE OF is_superuser`). It takes a transaction-level advisory lock (namespace 0x4144) and then rejects a third `is_superuser = true` row (`check_violation`, constraint name `admin_superuser_limit`). Deactivated superusers still count until revoked |
| `is_staff` | Written only by `admin_access.services.roles.refresh_staff_projection`: true when the account is eligible and has a live role, or is a break-glass superuser |
| Implicit-lock classes (doc 12 §5.5) | `AdminUserRole.user`, `AdminTotpDevice.user`, `AdminMfaEnrollment.user`: P (the target User is locked FOR UPDATE first). `assigned_by`, `issued_by`: B2. Role and permission FKs: N (reference data, catalogue sync) |
