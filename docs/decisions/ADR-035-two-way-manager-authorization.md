# ADR-035: Two-way family-manager authorization, permission selection and 30-day expiry

- **Status:** ACCEPTED for implementation (owner decisions DR-2026-11-20-O-1, -2, -4, 2026-11-20). Owner review pending.
- **Context:** FR-FAM-001…009; doc 05 §2; doc 14; doc 15 §4; ADR-034 (enumeration-safe invitations).

## Decision

1. **Flow A, invitation:** the owner invites by phone number and selects permissions (a template and/or individual codes). Sensitive codes need explicit confirmation and a recent owner step-up; Owner-only codes are refused. The background resolution creates the PENDING authorization with exactly the selection; the invitee accepts or rejects.
2. **Flow B, request:** an account asks to manage the profile of the account holding a phone number (`ManagerRequest`). It is enumeration-safe like ADR-034: same `202` answer for every valid number; a background task delivers it only to an eligible owner's personal profile. The owner accepts, selecting permissions with the same rules (the authorization is then ACTIVE: the requester consented by asking, the owner by accepting), or declines. The requester can cancel; the requester learns about the owner only when the owner answers.
3. **Selection is one shared rule** (`family.services.base.select_permissions`) used for invitations, request acceptance and later changes. Later changes grant or revoke individual permissions without a new authorization, recorded as `PERMISSIONS_GRANTED` / `PERMISSIONS_REVOKED` history rows, audited, with the manager notified.
4. **Managers never manage managers.** Every owner operation is filtered by the caller's own profile ownership; `/family-management/` is account-scoped (`X-Acting-Profile` refused), so a manager can't act there for the profile they manage; `manage_family_authorizations` and `manage_verification_submission` are Owner-only (migration `family.0004`), and a stored grant of an Owner-only permission is ignored. Requests carry only the caller's own identity; extra identity fields are ignored.
5. **30-day expiry:** invitations and requests carry `expires_at = sent + 30 days`. Acceptance after the deadline answers `409 invitation_expired`; the job (`family.expire_authorizations`, every 5 minutes) marks them EXPIRED with reason `NOT_ACCEPTED_WITHIN_30_DAYS`, expires a linked pending authorization, writes history and notifies the sender (always, the same way for resolved and unresolved invitations) and the recipient (when one exists).
6. **History:** `ManagerAuthorizationHistory` rows may now link an invitation or a request. Invitation-linked rows only record what the owner may see (created, cancelled, expired, answered); the background resolution is recorded on the authorization only.

## Consequences

- Doc 05 §2 rule 1 is amended (a request may start the process; the owner still decides). The optional expiry of an authorization (FR-FAM-007) is a separate rule and unchanged.
- Lock orders: invitations as in ADR-034; requests lock accounts (2) → profile (3) → request (domain) → inserts.
- Open: manager resignation (OD-05f), template pre-selection semantics (OD-05a), counterparty label (OD-05b), per-share approval (OD-05d).
