# Matermonial — Family Manager Permission Matrix

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-05; PROPOSED TRs: TR-16. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**Applied corrections:** DCR-06, DCR-10, DCR-32 (doc 20); G1 correction pass 2026-11-17 (DR-2026-11-17-C). The reconciled tiers and matrix are in **§9** [REC-BIZ, OD-05, OPEN]; until OD-05 is decided, §1–§8 remain the approved baseline and §9 is the recommended arrangement.

## 1. Purpose

This document defines the permission structure for family managers who manage matrimonial profiles on behalf of profile owners.

Permission groups are configurable templates. They must not be hardcoded as the only possible permission combinations.

## 2. Permission groups

Initial templates:

1. Standard Manager.
2. Communication Manager.
3. Advanced Manager.

The profile owner may customize permissions for each authorization.

## 3. Permission catalog

| Permission code | Description | Default sensitivity |
|---|---|---|
| `view_profile` | View represented profile | Normal |
| `edit_basic_info` | Edit permitted basic information | Normal |
| `edit_education` | Edit education | Normal |
| `edit_profession` | Edit profession | Normal |
| `edit_family_details` | Edit family details | Normal |
| `manage_photos` | Upload, update, or remove photos | Normal |
| `view_partner_preferences` | View partner preferences | Normal |
| `edit_partner_preferences` | Edit partner preferences | Normal |
| `search_profiles` | Search on behalf of profile | Normal |
| `view_interests` | View sent and received interests | Normal |
| `send_interests` | Express interest | Normal |
| `respond_to_interests` | Respond to received interests | Normal |
| `send_requests` | Send formal requests | Normal |
| `respond_to_requests` | Accept or decline requests | Normal |
| `withdraw_requests` | Withdraw pending requests | Normal |
| `view_connections` | View connections | Normal |
| `manage_relationship_progress` | Update relationship progress | Normal |
| `view_conversations` | View authorized conversations | Sensitive |
| `send_messages` | Send messages on behalf of profile | Sensitive |
| `upload_attachments` | Upload conversation attachments | Sensitive |
| `view_shared_documents` | View documents shared with profile | Sensitive |
| `share_documents` | Share owner's private documents | Sensitive |
| `manage_document_permissions` | Grant or revoke document access | Sensitive |
| `view_privacy_settings` | View privacy settings | Sensitive |
| `manage_privacy_settings` | Change privacy settings | Sensitive |
| `view_blocked_profiles` | View block list | Sensitive |
| `manage_blocked_profiles` | Block/unblock profiles | Sensitive |
| `view_hidden_profiles` | View Hide My Profile From list | Sensitive |
| `manage_hidden_profiles` | Hide/unhide profiles | Sensitive |
| `view_visitor_history` | View profile visitors | Sensitive |
| `manage_visitor_history` | Remove/clear visible visitor records | Sensitive |
| `manage_family_authorizations` | Invite and manage other managers | Sensitive |
| `view_verification_status` | View verification status | Sensitive |
| `manage_verification_submission` | Submit/resubmit verification | Sensitive |
| `view_financial_summary` | View subscription and credit summary | Sensitive |
| `manage_subscription` | Purchase or cancel subscription | Sensitive |
| `manage_account_security` | Change account security settings | Owner-only |
| `request_data_export` | Request account data export | Owner-only |
| `request_account_deletion` | Request account deletion | Owner-only |

## 4. Default group templates

### Standard Manager

Recommended permissions:

- View profile.
- Edit permitted profile information.
- Edit education and profession.
- View partner preferences.
- Search profiles.
- View interests and requests.
- Send interests.
- View connections.

### Communication Manager

Recommended permissions:

- View profile.
- Search profiles.
- View interests and requests.
- Send interests.
- Send and respond to formal requests.
- View connections.
- View conversations.
- Send messages.
- Manage relationship progress.

### Advanced Manager

Recommended permissions:

- Standard Manager permissions.
- Communication Manager permissions.
- Manage photos.
- Upload attachments.
- View authorized shared documents.
- Other permissions explicitly enabled by the owner.

Sensitive actions must not become automatically available merely because a group is named Advanced Manager. Sensitive permissions require explicit owner approval and any configured additional security checks.

## 5. Owner-only defaults

The following remain owner-only unless the platform explicitly supports delegation and the owner grants it:

- Managing family-manager authorizations.
- Changing privacy settings.
- Sharing private documents.
- Managing visitor-history removal.
- Account security.
- Data export.
- Account deletion.
- Payment/refund-sensitive account actions.

## 6. Permission evaluation

For every manager action:

1. Authenticate the actual user.
2. Resolve the represented profile.
3. Retrieve the relevant authorization.
4. Verify authorization status is ACTIVE.
5. Verify authorization has not expired.
6. Verify the required permission is granted.
7. Verify the target resource is accessible.
8. Check blocking, privacy, and restrictions.
9. Perform additional security verification if required.
10. Record the actual actor and represented profile.
11. Notify the owner where required.

## 7. Permission revocation

When a permission is revoked:

- Future requests must be denied immediately.
- Existing sessions must not retain stale permission access.
- Temporary URLs already issued may remain usable until expiry unless access is delivered through a revocable proxy.
- A permission-change history record must be created.
- The owner must be notified for sensitive permission changes.

> **G1 (DCR-32):** §9 proposes replacing the Normal/Sensitive/Owner-only labels with four tiers (N, S, H, O) and template semantics that resolve contradiction C-4 (templates listing Sensitive permissions while §4 forbids automatic grants).

## 8. Important security rule

The frontend may hide buttons for unavailable permissions, but the backend must enforce every permission independently.

## 9. Reconciled tiers and matrix (G1) [REC-BIZ, OD-05, OPEN]

> *Adapted from `docs/baseline/v4.6-F3/referenced/A4_v3.md` §7 (incorporated by reference, DR-2026-11-16-P1). Section references inside this block refer to that package. Step-up windows are TR-16 (PROPOSED). Editorial changes: headings renumbered under §9 (with the original A4 numbers in brackets) so they don't clash with doc 14 §7, and a conversational label in §7.1 was replaced with the neutral "Earlier proposal (v2)"; the text is otherwise verbatim.*

### 9.1 Family-Manager Permission Matrix (A4 §7)

#### 9.1.1 Reconciling communication permissions (A4 §7.1)

**[DECIDED] requirements in play:**
- FR-MSG-004 and SRS §3.2: authorized managers may communicate on behalf of a profile when the permission is granted.
- Doc 14 classifies `view_conversations`, `send_messages` and `upload_attachments` as Sensitive, and its Communication template lists the first two.
- Doc 14 §4: sensitive permissions must not become available automatically through a template.

**Earlier proposal (v2):** stripping these permissions from the Communication template defeated the template's purpose.

**v3 resolution (REC-BIZ, OD-05a)**, which keeps the Sensitive classification:
- A template may **propose** Sensitive communication permissions. Choosing the template **pre-selects** them on the assignment screen.
- **They aren't granted until the owner explicitly confirms the Sensitive section with owner step-up.** Applying a template alone never grants them, so nothing is automatic, and doc 14 §4 is satisfied.
- **Controls at use** [TR-16]: the manager must have re-authenticated within the last 12 hours. Every message records the actual manager account [DECIDED]. The owner gets a notification at grant time and a full activity view (ManagerActionLog). Each message is audited.
- **Document sharing and other particularly sensitive actions sit in a separate High tier** with stricter controls (below).

#### 9.1.2 Tiers (A4 §7.2)

| Tier | Grant | Use |
|---|---|---|
| **N** Normal | Template or individual grant | Authorization ACTIVE + permission granted |
| **S** Sensitive | **Explicit owner confirmation with owner step-up.** A template may only pre-select communication-class S permissions. Other S permissions are granted individually only. Owner notified. | Manager step-up within the window (12 h for communication, 10 min for others). Audited. |
| **H** High | Explicit individual owner grant with owner step-up. Never proposed by any template. | **Single-use step-up per action** + owner notified on every action + audit. `share_documents` also needs owner approval per share (REC-BIZ, OD-05d, from the FR-MSG-009 "recommended default"). |
| **O** Owner-only | Cannot be delegated in the MVP | — |

**Paused, expired, revoked, pending and rejected authorizations grant nothing [DECIDED].** Permissions are specific to each authorization [DECIDED].

#### 9.1.3 Templates and their purpose (A4 §7.3)

| Template | Purpose |
|---|---|
| **Standard** | Profile upkeep and discovery |
| **Communication** | Handling approaches and correspondence |
| **Advanced** | Standard + Communication + media and received documents |

**Matrix key:** ✓ granted by the template · ◆ pre-selected by the template, **granted only after explicit owner confirmation** · – not included.

| Code | Tier | Std | Comm | Adv |
|---|---|---|---|---|
| `view_profile` | N | ✓ | ✓ | ✓ |
| `edit_basic_info` (identity-locked fields always excluded) | N | ✓ | – | ✓ |
| `edit_education`, `edit_profession`, `edit_family_details` | N | ✓ | – | ✓ |
| `edit_location`, `edit_lifestyle`, `edit_languages` (new) | N | ✓ | – | ✓ |
| `manage_photos` | N | – | – | ✓ |
| `view_partner_preferences` | N | ✓ | – | ✓ |
| `edit_partner_preferences` | N | – | – | ✓ |
| `search_profiles` | N | ✓ | ✓ | ✓ |
| `view_profile_details` (new; **charged to the owner account**) | N | ✓ | ✓ | ✓ |
| `use_favorites` (new; scoped to the acting profile) | N | ✓ | ✓ | ✓ |
| `view_interests`, `view_requests` (new) | N | ✓ | ✓ | ✓ |
| `send_interests` | N | ✓ | ✓ | ✓ |
| `respond_to_interests` | N | – | ✓ | ✓ |
| `send_requests`, `respond_to_requests`, `withdraw_requests` (charged to the owner) | N | – | ✓ | ✓ |
| `view_connections` | N | ✓ | ✓ | ✓ |
| `manage_relationship_progress` | N | – | ✓ | ✓ |
| `request_photo_access` (new), `report_content` (new) | N | – | ✓ | ✓ |
| `view_conversations` | S (communication) | – | ◆ | ◆ |
| `send_messages` | S (communication) | – | ◆ | ◆ |
| `upload_attachments` | S (communication) | – | – | ◆ |
| `view_shared_documents` | S | – | – | ◆ |
| `manage_connections` (new: pause, close, complete, reopen) | S | – | – | – |
| `manage_photo_permissions` (new) | S | – | – | – |
| `view_privacy_settings`, `view_blocked_profiles`, `view_hidden_profiles`, `view_visitor_history`, `view_verification_status`, `view_financial_summary` | S | – | – | – |
| `manage_privacy_settings`, `manage_blocked_profiles`, `manage_hidden_profiles`, `manage_visitor_history`, `manage_subscription` | S | – | – | – |
| `share_documents` | **H** | – | – | – |
| `manage_document_permissions` | **H** | – | – | – |
| `manage_family_authorizations`, `manage_verification_submission` | **O** (REC-BIZ, OD-05c; doc 14 currently says S) | – | – | – |
| `manage_account_security`, `request_data_export`, `request_account_deletion`, `request_refund` (new) | O | – | – | – |

**Remaining owner decisions in this area:**
- **OD-05b:** whether the counterparty sees that a message was sent by a manager. Recommended: a neutral label, "Sent by an authorized family member"; the owner sees the manager's full identity.
- **OD-05c:** the two Owner-only reclassifications.
- **OD-05d:** owner approval per document share.

*— End of verbatim extract —*
