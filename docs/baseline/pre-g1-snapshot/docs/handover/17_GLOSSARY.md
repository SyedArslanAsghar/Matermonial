# Matermonial — Domain Glossary and Terminology

**Version:** 1.0  
**Date:** 11 November 2026

| Term | Definition |
|---|---|
| Account | Authentication and billing identity belonging to a registered user. |
| Matrimonial Profile | Profile representing the person seeking a matrimonial match. |
| Profile Owner | Account that owns a matrimonial profile. |
| Family Manager | Another account authorized to manage a profile. |
| Represented Profile | Profile on whose behalf an account is acting. |
| Actual Actor | Authenticated account that performed the operation. |
| Authorization | Owner-approved relationship allowing a manager to act for a profile. |
| Permission Group | Reusable template of permissions. |
| Sensitive Permission | Permission requiring explicit owner authorization and possibly extra verification. |
| Phone Verification | Proof of control over a phone number. |
| Identity Verification | Review of identity information/documents. |
| Partner Preference | Criteria describing the desired matrimonial partner. |
| Interest | Lightweight expression of interest in another profile. |
| Formal Request | Formal matrimonial request that uses request-credit rules. |
| Directional Cooldown | Restriction from one specified sender profile to one specified recipient profile. |
| Connection | Relationship record created after formal request acceptance. |
| Relationship Progress | Shared stage describing the status of matrimonial discussions. |
| Conversation | Messaging channel associated with a connection. |
| Shared Document | Document deliberately shared with another connected profile. |
| Profile Block | Unilateral restriction preventing discovery and communication. |
| Hidden Profile | Profile selected under Hide My Profile From without applying full blocking behavior. |
| Photo Permission | Authorization to access otherwise restricted profile photographs. |
| Visitor History | Record of profile visits shown according to subscription and privacy rules. |
| Private Browsing | Mode that hides the visitor's identity from normal visitor-history display. |
| Subscription Allowance | Credit quantity granted by a subscription billing period. |
| Purchased Credit | Credit acquired separately through a top-up purchase. |
| Credit Ledger | Append-only record of credit grants, deductions, expiry, and adjustments. |
| Billing Period | Period for which subscription benefits and allowances apply. |
| Idempotency | Guarantee that retrying an operation does not repeat its financial or business effect. |
| Transactional Outbox | Database-backed event queue written in the same transaction as a business operation. |
| Moderation Report | User-submitted complaint about an account, profile, or content. |
| Moderation Case | Review record that may group one or more reports. |
| Restriction | Explicit limitation applied to an account or profile. |
| Data Export | Secure archive of the requester's authorized personal data. |
| Data Retention Hold | Approved reason to preserve specific data beyond normal deletion timing. |
| Audit Log | Central record of significant system, security, financial, and administrative actions. |
| Domain History | Module-specific history of business state changes. |
| Feature Flag | Configuration that controls availability of a feature or integration. |
| MVP | Minimum Viable Product: the initial product scope defined in the SRS. |
| Post-MVP | Functionality excluded from the initial release unless separately approved. |

## Terminology rules

- Use "account" for authentication and billing identity.
- Use "profile" for the matrimonial person/profile.
- Use "manager" for an account authorized to act on another profile.
- Use "actual actor" for the account performing an action.
- Use "represented profile" for the profile on whose behalf the action is performed.
- Do not use "user" ambiguously in financial or authorization logic.
- Use "interest" and "formal request" as distinct business concepts.
- Use "block" and "hide" as separate privacy concepts.
- Use "subscription allowance" and "purchased credit" as separate financial concepts.