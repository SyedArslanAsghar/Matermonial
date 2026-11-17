# Matermonial — Family Manager Permission Matrix

**Version:** 1.0  
**Date:** 11 November 2026

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

## 8. Important security rule

The frontend may hide buttons for unavailable permissions, but the backend must enforce every permission independently.