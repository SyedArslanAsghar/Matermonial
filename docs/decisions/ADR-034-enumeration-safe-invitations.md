# ADR-034: Enumeration-safe family-manager invitations

- **Status:** ACCEPTED for implementation (owner instruction DR-2026-11-20-C-2, 2026-11-20). Owner review of Phases 2–4 pending.
- **Context:** KI-34; FR-FAM-001 ("invite another registered account"); doc 06 (no disclosure of account existence); CC-R50.

## Problem

The Phase 4 invite endpoint answered `201` with the manager's display name when the number belonged to an eligible account, and answered `400 invitee_not_available` otherwise. The owner's list also showed the pending authorization with the invitee's name. So a profile owner could find out whether any phone number belonged to an eligible account, and learn that account's first name. The amount of database work also differed between the two cases (timing).

## Decision

1. Every invite request that passes validation creates a **`ManagerInvitation`** and returns the **same `202` body**, built only from the owner's input: a masked number hint, the requested template, permissions and expiry, and the status `PENDING`. This happens whether the number is unregistered, unverified, inactive, deactivated or eligible.
2. Refusals depend only on the owner's own data:
   - the rate limit, which counts every attempt, including unregistered numbers
   - invalid input
   - the owner's own number
   - a number the owner already has a pending invitation for
   - a number that belongs to one of the owner's current managers
3. The request does the same database work either way: one account lookup, the same lock statement, one insert. A test asserts identical query counts. Eligibility is decided afterwards by the Celery task `family.resolve_manager_invitation`, scheduled after commit. If the number belongs to an eligible account, the task creates the PENDING `ProfileManagerAuthorization` and notifies the invitee. Otherwise it records an internal audit row (`family.invitation_unresolved`, no phone number) and nothing visible changes.
4. **The owner sees an authorization only after the invitee accepts.** Before that, owner endpoints treat never-accepted authorizations like missing ones (404), and the owner manages invitations: list them, and cancel with `POST /family-management/invitations/{id}/cancel/`, which revokes a linked pending authorization.
5. The phone number isn't stored. `phone_digest` is an HMAC (SUBJECT_HASH ring) used only to refuse duplicate pending invitations, and `phone_hint` is the masked display. `invitee` is internal and never serialized.
6. When the invitee responds, the invitation becomes `ACCEPTED` or `DECLINED`. A decline is visible to the owner because the invitee chose to respond. That disclosure is the invitee's own act, not the owner's probing.

## Consequences

- An invitation to a number with no eligible account stays PENDING until the owner cancels it. There is no TTL until OD-05e is decided, and a TTL should apply to both kinds of invitation the same way.
- An account that registers or verifies its phone **after** an invitation isn't linked to it. The owner can cancel and invite again.
- Lock order: authorization (1) before the invitation (domain level 7). Cancel reads the link and then locks in that order, retrying once if the task linked an authorization meanwhile. The task locks the accounts (2), the profile (3), then the invitation (7). The FK inventory classifies the new foreign keys.
- `family.0003` backfills invitation rows for authorizations that existed before it (local data only; nothing is deployed).
- Residual: response timing still includes the after-commit enqueue in both cases, and the remaining differences are scheduler noise. The per-owner rate limit (10/day by default) bounds probing.
