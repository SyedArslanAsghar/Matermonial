# Complete Software Requirements Specification

# Matermonial — Software Requirements Specification (SRS) and MVP Requirements

**Version:** 1.0  
**Date:** 11 November 2026  
**Status:** Development Handover Baseline

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the functional and non-functional requirements for Matermonial.

It describes the platform's intended users, business objectives, functional capabilities, workflows, access boundaries, constraints, and acceptance expectations.

It is intended for developers, testers, product owners, administrators, and Claude Code.

### 1.2 Product vision

Matermonial is a digital matrimonial platform designed to support serious matrimonial discovery while respecting privacy, family involvement, identity verification, user consent, and controlled communication.

The platform must support both individuals managing their own matrimonial profiles and authorized family members managing profiles on behalf of others.

### 1.3 Business objectives

The platform aims to:

1. Allow adults to register and create matrimonial profiles.
2. Provide identity and phone verification.
3. Support family-assisted profile management through explicit authorization.
4. Enable profile discovery and rule-based matching.
5. Support interests and formal matrimonial requests.
6. Manage request credits and subscription allowances.
7. Establish connections after request acceptance.
8. Enable controlled communication between connected profiles.
9. Protect profile photos, documents, contact information, and sensitive data.
10. Provide moderation, reporting, and administrative oversight.
11. Provide users with data export and account deletion capabilities.
12. Support web and mobile applications through a shared backend API.

# Matermonial — Software Requirements Specification (SRS)

**Document ID:** 01  
**Document Title:** Complete Software Requirements Specification and MVP Requirements  
**Project:** Matermonial  
**Version:** 1.0 — Handover Baseline  
**Status:** Consolidated specification; unresolved details must be identified separately  
**Audience:** Product Owner, Business Analyst, Software Architect, Backend Developer, Frontend Developer, Mobile Developer, QA Engineer and Claude Code

---

# 1. Introduction

## 1.1 Purpose

This document defines the functional and non-functional requirements of the Matermonial platform.

It is the primary reference for understanding:

- The business purpose of the platform.
- Its users and stakeholders.
- The MVP scope.
- Functional capabilities.
- Business constraints.
- User journeys.
- Privacy and security expectations.
- Acceptance criteria.
- Features that are excluded or deferred.

The document must be used together with the system architecture, database design, API specification, business rules, security specification and other handover documents.

## 1.2 Product Vision

Matermonial aims to provide a structured, secure and privacy-conscious matrimonial platform where individuals and authorized family members can discover suitable matches, manage introductions, communicate after mutual acceptance, and track relationship progress.

The platform must support both independent individuals and family-assisted matrimonial management.

It must not assume that every person using the platform is the owner of the profile being managed.

## 1.3 Core Product Principles

1. Privacy by default.
2. Adult-only participation.
3. Explicit profile ownership.
4. Owner-controlled family authorization.
5. Secure identity verification.
6. Mutual consent for matrimonial connections.
7. Transparent request and credit rules.
8. Controlled access to private photos and documents.
9. Auditable sensitive actions.
10. Secure communication.
11. Clear account and data lifecycle management.
12. Consistent experience across web and mobile applications.
13. Backend-enforced authorization.
14. Configurable business limits rather than scattered hardcoded values.

## 1.3.1 Core Product Principles

1. Privacy by default.
2. Adult-only participation.
3. Explicit profile ownership.
4. Owner-controlled family authorization.
5. Secure identity verification.
6. Mutual consent for matrimonial connections.
7. Transparent request and credit rules.
8. Controlled access to private photos and documents.
9. Auditable sensitive actions.
10. Secure communication.
11. Clear account and data lifecycle management.
12. Consistent experience across web and mobile applications.
13. Backend-enforced authorization.
14. Configurable business limits rather than scattered hardcoded values.

## 1.4 Intended Platforms

The product will provide:

- Web application: React, Vite and TypeScript.
- Android and iOS applications: React Native and Expo.
- Backend API: Django and Django REST Framework.
- Administrative interface: Django-based administration, with the approved SQLAdmin patterns where applicable.

All clients must use the same backend business rules and authorization model.

---

# 2. Stakeholders and User Types

## 2.1 Individual User / Profile Owner

An individual who owns an account and their personal matrimonial profile.

The owner can:

- Register and verify their account.
- Create and manage their matrimonial profile.
- Configure partner preferences.
- Search and discover other eligible profiles.
- Send and receive interests.
- Send, accept, decline or withdraw formal requests according to permissions.
- Manage connections.
- Communicate with connected profiles.
- Control profile visibility and media access.
- Invite and authorize family managers.
- Manage subscriptions and credits.
- Access account history and privacy controls.
- Request a data export.
- Request account deletion.

## 2.2 Family Manager

A family member or trusted person authorized by a profile owner to manage that owner's matrimonial profile.

A manager:

- Must have their own authenticated account.
- Must receive an invitation from the profile owner.
- Must explicitly accept the invitation.
- Can perform only the actions permitted by their active authorization.
- Cannot grant themselves permissions.
- Cannot continue accessing a profile after authorization is paused, revoked or expired.
- Must have their actions attributed to their own account.

A manager may manage multiple profiles if separately authorized by each owner.

## 2.3 Admin

An authorized platform administrator responsible for operational and administrative tasks.

Admin capabilities depend on assigned roles and permissions.

Examples include:

- User support.
- Verification review.
- Moderation.
- Subscription and package configuration.
- Payment investigation.
- Platform configuration.
- Feature flag management.
- Audit review.

Administrative access must follow least privilege.

## 2.4 Moderator

An authorized staff member responsible for reviewing reports and taking moderation actions.

Moderators must not receive unrestricted access to all user data.

Their access must be limited to assigned responsibilities.

## 2.5 Staff / Support Agent

A platform staff member who handles support cases and user assistance according to assigned permissions.

Support staff must not automatically receive access to private documents, conversations or identity verification files.

## 2.6 External Service Providers

External providers may include:

- SMS/OTP gateway.
- Email provider.
- Payment gateway, initially JazzCash.
- Push notification services.
- Object storage.
- Redis and background-processing infrastructure.

External services must be accessed through centralized provider abstractions.

---

# 3. User Eligibility and Account Rules

## FR-001 — Adult Eligibility

The platform is restricted to individuals aged 18 or older.

- The system must collect date of birth as part of the required profile information.
- Age must be calculated from date of birth.
- Date of birth must not be exposed publicly.
- Users under 18 must not become eligible for matrimonial participation.
- Eligibility checks must be enforced by the backend.

The exact handling of an underage registration attempt must be consistent across registration, profile completion and identity verification.

## FR-002 — Account Registration

A user must be able to register using:

- Phone number.
- Password.
- Required personal registration details.

Email is optional.

Phone numbers must be normalized to E.164 format.

A phone number must not be associated with multiple active accounts unless an explicitly approved account-recovery or migration process permits it.

## FR-003 — Phone Verification

Phone verification and identity verification are separate processes.

Recommended configurable defaults:

| Setting | Default |
|---|---:|
| OTP validity | 5 minutes |
| Resend cooldown | 60 seconds |
| Maximum verification attempts | 5 |
| Maximum OTP requests per hour | 5 |

Requirements:

- Store OTP hashes, never plaintext OTP values.
- Expire OTPs automatically.
- Limit resend and verification attempts.
- Prevent reuse of an already consumed OTP.
- Use generic responses that do not reveal whether another account owns a phone number.
- Record verification attempts and relevant security events.
- Keep provider credentials outside source code.

These limits must be configurable through centralized settings.

## FR-004 — Account and Profile Separation

An account and a matrimonial profile are different concepts.

- One account owns one personal matrimonial profile.
- One account may manage additional profiles through explicit family-manager authorization.
- The profile owner remains the owner even when a manager performs actions.
- Manager authorization does not transfer profile ownership.
- Account deactivation and profile visibility must be handled as separate concerns.

## FR-005 — Account Audit Information

The account model must support:

- `created_at`
- `created_by`
- `updated_at`
- `updated_by`
- `deactivated`, default `false`
- `deactivated_reason`

System-generated creation and update actions must preserve the actual actor where applicable.

## FR-006 — Account Deactivation

The platform must support account deactivation with a recorded reason.

Deactivation must be distinct from account deletion and temporary moderation restrictions.

The system must define and consistently enforce what account capabilities are disabled during deactivation.

An inactive or deactivated account must not bypass security or authorization restrictions through an existing session.

## FR-007 — Authentication and Session Security

The system must:

- Use secure password hashing.
- Support secure login and logout.
- Support password recovery.
- Support session/token revocation.
- Record relevant login and security events.
- Provide session and device history.
- Protect authentication endpoints against abuse.
- Avoid exposing credentials or tokens in logs.

Detailed token lifetimes, refresh-token rotation and session policies are specified in Document 06.

---

# 4. Matrimonial Profile Requirements

## FR-008 — Profile Creation

A verified and eligible account must be able to create and complete its personal matrimonial profile.

Profile information is divided into logical sections rather than one unrestricted text field.

The profile should support:

1. Basic information.
2. Personal and demographic details.
3. Religion and community.
4. Location and residence.
5. Family details.
6. Education.
7. Profession and employment.
8. Financial information.
9. Lifestyle.
10. Languages.
11. Photos and media.
12. Partner preferences.

Profile completion must be calculated from defined required fields and should not be based on arbitrary frontend calculations.

## FR-009 — Profile Status

The system must distinguish profile lifecycle from profile visibility.

The proposed profile lifecycle is:

- DRAFT
- PENDING_REVIEW
- ACTIVE
- PAUSED
- SUSPENDED
- CLOSED

Visibility is managed separately.

A profile may be ACTIVE but hidden from match search.

A profile may not become publicly discoverable merely because it has a valid account.

All required eligibility, verification, moderation and owner-controlled visibility conditions must be satisfied.

## FR-010 — Profile Verification

Identity verification is separate from phone verification.

Identity verification must support:

- Not submitted.
- Pending review.
- Under review.
- Approved.
- Rejected.
- Resubmission required.
- Cancelled.

A rejected identity verification may be resubmitted using new live pictures and a new review process.

The system must preserve verification history and reviewer decisions.

## FR-011 — Post-Verification Activation

Following identity approval, the profile defaults to Visible in Match Search, subject to all other activation and eligibility checks.

This default must not override:

- Account deactivation.
- Profile suspension.
- Moderation restrictions.
- Age eligibility.
- Owner privacy restrictions.
- Blocking or hidden-profile rules.
- Other required activation checks.

## FR-012 — Verified Field Restrictions

Identity-verified fields must be protected from ordinary edits.

Education and professional information remain editable.

The implementation must identify exactly which fields are locked by identity approval.

Any correction to a locked field must follow a controlled, auditable process.

## FR-013 — Profile Location

The profile must support worldwide location information.

Location filters may include:

- Country.
- State or province.
- City.
- Area or locality.
- Residence type.

Nationality must not restrict worldwide location search.

A person's current residence and nationality are separate concepts.

## FR-014 — Education and Profession

A profile may contain multiple education records.

Professional details must support relevant employment and business information.

Income must use Decimal values rather than floating-point storage.

Income must include currency and frequency, where applicable.

The system must not assume that all users earn monthly or use the same currency.

## FR-015 — Family and Lifestyle Details

The profile must support appropriate family and lifestyle information, including configurable fields for:

- Family structure.
- Family occupations.
- Family values and description.
- Sibling information.
- Height.
- Diet.
- Smoking.
- Drinking.
- Exercise.
- Other approved lifestyle information.

Sensitive fields must have defined visibility rules.

## FR-016 — Profile Languages

The platform must support English and Urdu.

Urdu interfaces must support right-to-left layout.

Profile language information must support multiple languages and proficiency levels.

## FR-017 — Profile Photos

Users must be able to upload and manage profile photos according to the media and moderation rules.

The system must support:

- Multiple photos.
- Primary photo selection.
- Private storage.
- Moderation status.
- Upload validation.
- Controlled access.
- Soft deletion or equivalent retained audit history.

A photo must never become publicly accessible simply because its storage URL is known.

---

# 5. Partner Preference Requirements

## FR-018 — Partner Preference Management

A profile owner must be able to configure partner preferences.

Preferences may include:

- Preferred age range.
- Gender.
- Marital status.
- Religion.
- Community.
- Caste or subcast.
- Nationality.
- Country, city and residence.
- Education.
- Profession.
- Languages.
- Financial expectations.
- House ownership.
- Employment.
- Business ownership.
- Additional requirements.

## FR-019 — Nullable Boolean Preferences

The following fields must support nullable Boolean values:

- `own_house`
- `job`
- `business`

Meaning:

| Value | Meaning |
|---|---|
| `true` | Explicitly prefers or requires yes |
| `false` | Explicitly prefers or requires no |
| `null` | No preference |

Null must not be treated as false.

## FR-020 — Financial Preference Range

The partner preference must support:

- `minimum_earning`: nullable integer.
- `maximum_earning`: nullable integer.
- Earning currency.
- Earning frequency.

When both minimum and maximum are provided, minimum must not exceed maximum.

The system must compare income only when the currency and frequency are compatible or a reliable conversion rule has been explicitly configured.

## FR-021 — Optional Criteria

Optional preferences must not automatically disqualify a candidate.

The matching engine must distinguish:

- Hard eligibility rules.
- Explicit strict criteria.
- Optional preferences.
- Ranking and recommendation criteria.

For the MVP, use rule-based matching.

AI-driven matching is outside the initial MVP unless separately approved.

---

**End of Document 01 — Part 1**



## 2. Scope

### 2.1 MVP scope

The MVP includes:

- Account registration and authentication.
- Phone OTP verification.
- Optional email verification.
- Adult eligibility checks.
- Matrimonial profile creation and editing.
- Profile photographs and media moderation.
- Identity verification workflow.
- Partner preferences.
- Family-manager authorization and permissions.
- Profile search and rule-based matching.
- Favorites and private notes.
- Profile-view allowances and billing.
- Interests and formal matrimonial requests.
- Request acceptance, rejection, withdrawal, and expiration.
- Directional 30-day cooldown after decline or expiration.
- Connections and relationship progress.
- Text messaging and shared documents.
- Privacy controls, blocking, and hidden profiles.
- Photo access requests and permissions.
- Subscription plans and credit packages.
- JazzCash payment integration.
- In-app, email, SMS, and push notification architecture.
- Moderation reports and administrative actions.
- Data export.
- Account deletion with recovery period.
- Audit logs and administrative configuration.
- English and Urdu localization.
- Responsive web and mobile application support.

### 2.2 Explicitly excluded from MVP

Unless separately approved, the following are post-MVP:

- AI-based matching and machine-learning recommendations.
- Voice and video calling.
- Microservices architecture.
- Automated matrimonial consultants or human matchmaking services.
- Advanced AI profile analysis.
- Complex recommendation models.
- Unapproved third-party payment gateways.
- Unapproved social-network integrations.
- Unapproved automatic subscription renewal behavior.

Rule-based matching is the MVP matching approach.

## 3. User roles and stakeholders

### 3.1 Individual account owner

An account owner can:

- Register and authenticate.
- Own one personal matrimonial profile.
- Create and maintain their profile.
- Manage partner preferences.
- Complete verification.
- Search and discover profiles.
- Send and receive interests and requests.
- Manage connections and conversations.
- Purchase subscriptions and credits.
- Control privacy settings.
- Authorize family managers.
- View account and profile activity.
- Request personal data export.
- Request account deletion.

### 3.2 Family manager

A family manager is an existing authenticated account that receives explicit authorization to manage another person's matrimonial profile.

A manager may:

- Edit the profile if authorized.
- Upload or manage photos if authorized.
- Search profiles on behalf of the owner.
- Send, accept, or decline requests if authorized.
- Communicate through the represented profile if authorized.
- View requests and connection information within their permissions.

A manager does not become the profile owner and does not gain unrestricted access to the owner's account.

Sensitive permissions are owner-only by default.

### 3.3 Administrator

Administrators manage platform configuration, subscriptions, payment settings, users, support, and operational functions according to assigned permissions.

### 3.4 Moderator

Moderators review reports, evidence, content, and cases. They can apply only the restrictions and moderation actions permitted by their assigned role.

### 3.5 Support staff

Support staff handle user support cases and operational questions. They must not receive unrestricted access to identity documents, private conversations, or other sensitive data.

## 4. Account and authentication requirements

### FR-ACC-001: Registration

The platform shall allow a user to register using a mobile phone number and password.

### FR-ACC-002: Phone verification

The platform shall verify phone ownership through OTP before enabling protected matrimonial activities.

### FR-ACC-003: Email

Email shall be optional during initial registration. Email verification shall be available when an email address is supplied or when required by a protected workflow.

### FR-ACC-004: Adult eligibility

The platform shall restrict matrimonial participation to users aged 18 or older.

### FR-ACC-005: Authentication

The platform shall provide secure login, logout, password reset, session/token management, and security-event tracking.

### FR-ACC-006: Account/profile separation

An account and a matrimonial profile shall be separate entities. An account may own one personal profile and may also manage other profiles through authorization.

### FR-ACC-007: Account audit fields

Account records shall maintain:

- `created_at`
- `created_by`
- `updated_at`
- `updated_by`
- `deactivated`, default false
- `deactivated_reason`

### FR-ACC-008: Phone normalization

Phone numbers shall be normalized to E.164 format and unique per account.

### FR-ACC-009: Limited browsing

Unverified users may browse a limited set of public profile information according to platform policy. They shall not perform protected request or connection actions until eligibility requirements are met.

## 5. Matrimonial profile requirements

### FR-PRO-001: Profile creation

An eligible account shall be able to create one personal matrimonial profile.

### FR-PRO-002: Profile sections

A profile shall support:

- Basic information.
- Demographic information.
- Religion and community.
- Nationality.
- Location and residence.
- Education.
- Profession and employment.
- Income information.
- Family information.
- Lifestyle information.
- Languages.
- Profile photographs.
- Partner preferences.

### FR-PRO-003: Date of birth privacy

The platform shall not publicly expose a user's full date of birth. Age may be calculated and displayed according to privacy settings.

### FR-PRO-004: Education and profession

Education and professional details shall remain editable after identity verification, subject to normal validation and audit requirements.

### FR-PRO-005: Verified information

Fields classified as identity-verified shall be protected from unauthorized modification. Any correction process shall use an explicit review workflow.

### FR-PRO-006: Profile visibility

The platform shall support:

- Visible in match search.
- Visible after acceptance, according to configured rules.
- Hidden.

Visibility is separate from photo and document access permissions.

### FR-PRO-007: Profile activation

After identity verification is approved, the profile shall default to Visible in Match Search, provided all other activation and eligibility requirements are satisfied.

### FR-PRO-008: Profile photographs

Users shall be able to upload multiple profile photographs. The platform shall support primary-photo selection, moderation status, private storage, and controlled delivery.

## 6. Partner preference requirements

Users shall be able to specify desired partner criteria, including:

- Age range.
- Gender.
- Marital status.
- Religion.
- Community.
- Caste/sub-caste.
- Nationality.
- Country, state/province, city, and area.
- Education.
- Language.
- Employment.
- Profession.
- Business.
- Residence type.
- Own house.
- Earning range.
- Additional requirements.

The following fields shall be nullable Boolean values:

- `own_house`
- `job`
- `business`

Interpretation:

- `true`: Yes is preferred/required according to the selected matching rule.
- `false`: No is preferred/required according to the selected matching rule.
- `null`: No preference.

Earning fields:

- `minimum_earning`: nullable Integer.
- `maximum_earning`: nullable Integer.
- Earning currency and frequency must be stored separately.
- Minimum earning must not exceed maximum earning.

Income values in profile records shall use Decimal, not floating-point types.

## 7. Verification requirements

### FR-VER-001: Phone verification

Phone verification shall be independent of identity verification.

### FR-VER-002: Identity submission

Users shall be able to submit the configured identity information and required documents.

### FR-VER-003: Review workflow

Identity verification shall support:

- Not submitted.
- Pending review.
- Under review.
- Approved.
- Rejected.
- Resubmission required.
- Cancelled.

### FR-VER-004: Rejection and resubmission

A rejected applicant shall be able to resubmit using new live pictures and required information for a new review.

### FR-VER-005: Duplicate document detection

The platform shall use a protected HMAC-based fingerprint for duplicate identity-document detection. It shall not store a plain hash of predictable identity numbers.

### FR-VER-006: Reviewer audit

Every verification decision shall record reviewer, decision, timestamp, and reason.

## 8. Family management requirements

### FR-FAM-001: Authorization invitation

A profile owner shall be able to invite another registered account to manage their profile.

### FR-FAM-002: Acceptance

The invited manager must explicitly accept the authorization.

### FR-FAM-003: Permission assignment

The owner shall be able to assign a permission group and configure individual permissions.

### FR-FAM-004: Starter permission groups

The system shall provide configurable starter templates:

- Standard Manager.
- Communication Manager.
- Advanced Manager.

These are templates, not immutable roles.

### FR-FAM-005: Sensitive permissions

Sensitive permissions shall be owner-only by default. Examples include:

- Changing privacy settings.
- Sharing private documents.
- Managing other managers.
- Viewing or removing visitor history.
- Performing sensitive account/profile actions.

Explicit permission, additional security verification, notification, and audit shall be required where configured.

### FR-FAM-006: Authorization lifecycle

An authorization shall support:

- Pending.
- Active.
- Paused.
- Expired.
- Revoked.
- Rejected.

### FR-FAM-007: Expiry

Authorization expiry shall be optional. The default is no expiry unless the owner sets one.

### FR-FAM-008: Owner control

The owner shall be able to pause, reactivate, or revoke a manager's authorization.

A paused or revoked manager shall immediately lose the relevant access.

### FR-FAM-009: Activity tracking

The system shall record manager actions and profile access history, including device/browser and approximate location where available.

## 9. Matching and search requirements

### FR-MAT-001: Search

Eligible users shall be able to search profiles using supported demographic, location, religion, community, education, profession, employment, business, and partner-preference criteria.

### FR-MAT-002: Worldwide search

Search shall support international locations. Nationality shall not be used as a global restriction that prevents otherwise eligible profiles from being discovered.

### FR-MAT-003: Rule-based matching

The MVP shall use deterministic rule-based matching.

### FR-MAT-004: Optional criteria

An unspecified optional preference shall not automatically disqualify a candidate.

### FR-MAT-005: Eligibility filters

Search and matching shall exclude profiles that are blocked, hidden from the requester, suspended, non-visible, or otherwise ineligible.

### FR-MAT-006: Favorites

Users shall be able to save profiles as favorites and add private notes.

Private notes shall be visible only to the account that created them.

### FR-MAT-007: Profile views

Profile detail views may consume profile-view allowances according to subscription and credit rules. Search-result impressions shall not consume profile-view credits.

## 10. Interests and matrimonial requests

### FR-REQ-001: Express interest

Eligible users shall be able to express interest in another eligible profile.

### FR-REQ-002: Interest response

The recipient may:

- Show Interest Back.
- Send a Formal Request.
- Decline Interest.

### FR-REQ-003: Declined interest history

A declined interest shall move to history. The original sender shall not be able to send another interest to the same recipient for 30 days.

This cooldown is directional: it applies from the original sender to the recipient, not automatically in the reverse direction.

### FR-REQ-004: Formal requests

Formal requests shall be subject to the applicable request-credit rules.

### FR-REQ-005: Duplicate requests

The system shall prevent duplicate active requests between the same two profiles in either direction.

### FR-REQ-006: Request expiry

A pending formal request shall expire after three calendar months.

### FR-REQ-007: Withdrawal

The original sender may withdraw a pending request.

### FR-REQ-008: History

Every request status transition shall be preserved in an append-only history.

### FR-REQ-009: Atomic financial operation

Request creation, credit deduction, and request-history creation shall occur atomically. A failure in any required operation shall roll back the complete operation.

## 11. Connections and relationship progress

### FR-CON-001: Connection creation

An accepted formal request shall create a connection between the two profiles within the same database transaction.

### FR-CON-002: Connection states

Connections shall support:

- Active.
- Paused.
- Completed.
- Closed.

### FR-CON-003: Reopening

A closed connection shall require mutual confirmation to reopen. A completed connection shall not be reopened by default.

### FR-CON-004: Relationship progress

The system shall support:

- Request Accepted.
- Initial Communication.
- Discussion in Progress.
- Meeting Planned.
- Meeting Completed.
- Proposal / Serious Discussion.
- Engaged.
- Closed.

### FR-CON-005: Progress history

Every progress update shall record the previous status, new status, actor, represented profile, and timestamp.

### FR-CON-006: Shared notes

Relationship progress notes shall be shared with the connected party according to the connection's access rules.

## 12. Messaging and shared documents

### FR-MSG-001: Conversation creation

One conversation shall be associated with each connection.

### FR-MSG-002: Participants

The MVP shall support exactly two profile participants in a conversation.

### FR-MSG-003: Messaging eligibility

Messaging shall be allowed only when the connection is active and no blocking or restriction rule prevents communication.

### FR-MSG-004: Manager communication

An authorized family manager may communicate on behalf of a profile when the relevant permission is granted. The actual manager account shall be recorded.

### FR-MSG-005: Message history

Message history shall be retained according to platform retention rules. User-side hiding or deletion shall not silently erase legitimate history for the other participant.

### FR-MSG-006: Attachments

Message attachments shall be validated, stored privately, scanned where supported, and delivered using controlled access.

### FR-MSG-007: Shared documents

Users may upload and share documents separately from identity-verification documents and message attachments.

### FR-MSG-008: Document permission

Document access shall require a separate permission record that can expire or be revoked.

### FR-MSG-009: Sensitive sharing

Family-manager document sharing shall require explicit permission, additional security verification, and immediate owner notification. Owner approval is recommended as the default policy.

### FR-MSG-010: MVP exclusions

Voice and video calling are excluded from MVP.

## 13. Privacy and media access

### FR-PRI-001: Blocking

A user shall be able to block another profile unilaterally and privately.

Blocking shall prevent new discovery, requests, and communication, and disable applicable media/document access.

Existing records shall be preserved.

### FR-PRI-002: Unblocking

Unblocking shall restore eligibility only where no other restriction applies.

### FR-PRI-003: Hide My Profile From

A user shall be able to hide their profile from selected profiles without blocking them.

The selected profile shall not find the owner through search or recommendations and shall not send new interests or requests.

The selected person shall not be notified.

Hiding shall not terminate an existing accepted connection or automatically revoke existing photo/document permissions.

### FR-PRI-004: Hidden-profile management

The owner shall have a private page to view and unhide selected profiles.

Only the owner may manage the list by default. A family manager requires explicit owner-granted permission.

### FR-PRI-005: Photo permissions

Photo access shall support:

- Seven-day access.
- Thirty-day access.
- Manual expiration/revocation.

### FR-PRI-006: Visitor history

Visitor history shall be an Advance/Premium feature, with a recommended configurable 90-day retention period.

### FR-PRI-007: Private browsing

Private browsing shall prevent the visitor's identity from appearing in the owner's normal visitor-history view.

### FR-PRI-008: Visitor history removal

An owner may remove an individual visitor from visible visitor history. Removal shall not block that visitor or prevent them from appearing again later. Security and audit records shall remain intact.

### FR-PRI-009: Private media

Private media shall use private storage and short-lived signed URLs or an equivalent controlled delivery mechanism.

Previously downloaded copies cannot be remotely recalled.

## 14. Subscription and credit requirements

### FR-SUB-001: Subscription plans

Administrators shall configure plans, durations, prices, currencies, benefits, and availability.

### FR-SUB-002: Subscription allowances

Plans may grant request and profile-view allowances for each billing period.

### FR-SUB-003: Allowance expiry

Unused monthly subscription allowances shall expire at the end of the billing period and shall not roll over.

### FR-SUB-004: Purchased top-ups

Users shall be able to purchase separate request-credit top-up packages without upgrading their subscription.

Purchased top-up credits shall not expire while unused.

### FR-SUB-005: Separate balances

Subscription allowances, purchased request credits, and profile-view credits shall remain distinguishable.

### FR-SUB-006: Consumption order

Subscription allowances shall be consumed before purchased credits.

### FR-SUB-007: Payment history

All purchases, payments, deductions, refunds, expirations, and adjustments shall be recorded in an auditable transaction ledger.

### FR-SUB-008: Failed renewal

A three-day grace period shall be supported for failed subscription renewal. Paid benefits and new allowances shall remain suspended until payment is confirmed.

### FR-SUB-009: Cancellation

Cancellation shall stop future renewal. Existing paid benefits continue until the paid period ends, subject to refund and account restrictions.

### FR-SUB-010: Refunds

Unused purchased credits may be reversed through an auditable transaction when a refund is approved. Already-consumed credits require review; the system shall not create negative balances.

### FR-SUB-011: Account billing identity

Credits shall be billed to the account, not to the family manager's personal account. The actual manager and represented profile shall still be recorded.

### FR-SUB-012: Profile-view billing

A profile detail view shall be billable at most once per account-target profile within a 24-hour billing window, subject to the allowance policy.

## 15. Notifications

The platform shall support:

- In-app notifications.
- Email.
- SMS.
- Push notifications.

Users shall be able to configure ordinary notification preferences by channel and category.

Essential security and authentication notifications shall not be disabled through ordinary preferences.

SMS and push content shall be generic and shall not disclose private profile details, OTP values, conversation contents, documents, or contact information.

Notifications shall use a transactional outbox and retryable background delivery.

Templates shall support English and Urdu with a configured fallback language.

## 16. Moderation and reporting

Users shall be able to report accounts, profiles, photographs, messages, and shared documents.

The MVP shall require authenticated reporting.

A report alone shall not automatically suspend an account or remove content unless an explicitly approved emergency rule applies.

The platform shall support:

- Report categories and reasons.
- Private evidence upload.
- Evidence scanning.
- Case grouping.
- Moderator assignment.
- Review and action history.
- Temporary restrictions.
- Appeals.
- Elevated approval for critical permanent actions.

Reporters' identities shall be confidential to the reported person.

Moderators shall not review cases where they have a conflict of interest.

## 17. Data export and account deletion

### FR-DAT-001: Download My Data

Users shall be able to request an export of their own data.

### FR-DAT-002: Export format

Exports shall be packaged as ZIP files containing structured JSON and eligible media files.

### FR-DAT-003: Export identity confirmation

Identity confirmation shall be required before processing sensitive exports.

### FR-DAT-004: Export scope

The export shall include data the requester is authorized to access, including their account, profile, preferences, eligible media, requests, connections, favorites/private notes, authorized conversation history, subscription/payment/credit records, and relevant account activity.

It shall exclude other people's private or restricted information, internal moderation evidence, and identity-verification documents by default.

### FR-DAT-005: Download expiry

The generated export shall be available for seven days. Secure download links shall expire after 24 hours.

### FR-DAT-006: Account deletion

Users shall be able to request account deletion after identity confirmation.

### FR-DAT-007: Recovery period

A 30-day recovery period shall apply before irreversible deletion processing begins.

### FR-DAT-008: Deletion processing

Deletion shall be asynchronous, retryable, and idempotent.

### FR-DAT-009: Retention exceptions

Legally required financial, security, fraud, moderation, and audit records may be retained under documented retention policies and justified holds.

### FR-DAT-010: Manager deletion

Deleting a manager account shall revoke that manager's authorizations but shall not delete profiles owned by other users.

## 18. Administrative requirements

The platform shall provide administrative capabilities for:

- User and profile management.
- Verification review.
- Moderation and appeals.
- Subscription plans and benefits.
- Credit packages.
- Payment reconciliation.
- Notification types and templates.
- Feature flags.
- System configuration.
- Support cases.
- Maintenance windows.
- Audit history.
- Administrative role and permission management.

Administrative permissions shall follow least privilege and be audited.

## 19. Non-functional requirements

### 19.1 Security

- Passwords shall use Django-supported secure password hashing.
- OTPs shall be stored as hashes, not plaintext.
- Secrets shall be stored outside source control.
- APIs shall enforce authentication and object-level authorization.
- Private files shall never be publicly accessible by default.
- Payment callbacks shall be verified and idempotent.
- Sensitive actions shall be audited.
- Production administration shall use MFA.

### 19.2 Privacy

- Collect only necessary personal data.
- Avoid exposing full date of birth, identity numbers, contact details, and private documents.
- Apply field-level access rules.
- Keep family-manager permissions separate from account ownership.
- Keep private notes private.
- Restrict internal moderation and security data.

### 19.3 Reliability

- Financial operations shall be transactional.
- Background tasks shall support retries and idempotency.
- Notifications shall not be lost when a business transaction commits.
- Critical errors shall be logged and monitored.
- Database backups and restoration procedures shall be documented and tested.

### 19.4 Performance

The application shall use pagination for list endpoints, database indexes for common search/filter fields, query optimization, and caching only where consistency and privacy permit.

Performance targets shall be measured under an agreed deployment and load profile before production launch.

### 19.5 Scalability

The modular monolith shall permit horizontal scaling of web workers and Celery workers without changing the core domain architecture.

### 19.6 Maintainability

Code shall use clear module boundaries, service layers, selectors, typed interfaces where appropriate, automated tests, linting, and API documentation.

### 19.7 Localization

The platform shall support English and Urdu. Urdu interfaces shall support right-to-left layout, translated templates, and appropriate date/number presentation.

## 20. MVP acceptance principles

The MVP may be considered functionally ready when:

1. A user can register, verify their phone, and authenticate securely.
2. An adult user can create and complete a matrimonial profile.
3. Identity verification can be submitted, reviewed, approved, rejected, and resubmitted.
4. A user can authorize a family manager and control that manager's permissions.
5. Search respects profile visibility, blocking, hidden profiles, and eligibility.
6. A user can express interest and send a formal request under the credit rules.
7. Declines and expirations enforce the directional cooldown.
8. Accepted requests create connections reliably.
9. Active connections can communicate through text messaging.
10. Private media and shared documents enforce permissions.
11. Subscriptions, allowances, top-ups, and payments maintain accurate ledgers.
12. Notifications are delivered through configured channels with retry handling.
13. Moderation reports and actions are auditable.
14. Data exports and deletion workflows enforce identity, privacy, and retention rules.
15. Web and mobile clients can use the documented API.
16. Automated tests cover critical business, security, and financial workflows.

## 21. Requirements traceability

Every functional requirement shall be mapped during implementation to:

- Owning Django module.
- Relevant database models.
- API endpoint or admin workflow.
- Authorization rule.
- Automated tests.
- Acceptance criteria.

The traceability matrix shall be maintained in the project documentation and updated whenever a requirement changes.

## 22. Open implementation details

The following details require configuration or confirmation before production activation:

- Final subscription prices and benefit quantities.
- Final request-credit and profile-view package quantities.
- JazzCash merchant credentials and current integration contract.
- SMS and email providers and production credentials.
- Identity verification document types and operational review policy.
- Final legal/privacy wording and jurisdiction-specific retention obligations.
- Production performance and availability targets.
- AWS region, instance sizing, domain, and certificate details.

These open items shall not block implementation of provider interfaces, configuration models, mock services, and test workflows.
