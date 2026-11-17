# Matermonial — Database Design: 16 Modules

**Version:** 1.0  
**Date:** 11 November 2026  
**Database:** PostgreSQL  
**Primary key convention:** UUID for major domain entities

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
- `email`: nullable, unique when supplied.
- `password`: Django password hash.
- `first_name`.
- `last_name`.
- `date_joined`.
- `is_active`.
- `is_staff`.
- `is_superuser`.
- `phone_verified`.
- `email_verified`.
- `deactivated`: Boolean, default false.
- `deactivated_reason`: nullable text.
- `created_at`.
- `created_by`: nullable user FK where applicable.
- `updated_at`.
- `updated_by`: nullable user FK where applicable.

Do not expose password hashes through APIs.

### 2.2 AccountSecurityEvent

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

Account is the primary billing identity. A manager must not bypass the same account's billing limit by switching represented profiles.

Use a 24-hour account-target billing window.

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
- `status`: REQUEST_ACCEPTED, INITIAL_COMMUNICATION, DISCUSSION_IN_PROGRESS, MEETING_PLANNED, MEETING_COMPLETED, PROPOSAL_SERIOUS_DISCUSSION, ENGAGED, CLOSED.
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
- `status`: ACTIVE, PAUSED, CLOSED.
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

Unique constraint: document + recipient profile.

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

Maintain separate balances for:

- Subscription request credits.
- Purchased request credits.
- Subscription profile-view credits.
- Purchased profile-view credits.

Balances are operational summaries. The transaction ledger remains the authoritative history.

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
- `security_notifications_enabled`.
- `language`.
- `quiet_hours_start`.
- `quiet_hours_end`.
- `timezone`.
- `updated_at`.

Essential security/auth notifications must remain enabled.

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
16. One document permission per document/recipient pair.
17. One wallet per user.
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