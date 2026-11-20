# Owner Decision Report: OD-05 and TR-16 (KI-35)

**Prepared:** 2026-11-20, under DR-2026-11-20-C-6. **Status:** for owner decision. Nothing here is approved. OD-05 and TR-16 stay **OPEN / PROPOSED**, and no behaviour that depends on them has been implemented.

**Sources:**
- doc 19 (OD-05a–f, TR-16)
- `docs/baseline/v4.6-F3/referenced/A4_v3.md`: §3 (TR-16), §4 (OD-05 row), §7 (tiers and templates), §9 step 10, §13
- doc 14 §1–§8 (approved) and §9 (REC-BIZ)
- doc 15 §4
- FR-FAM-004…006

## 1. Summary

| Item | Question | Recommendation | Urgency |
|---|---|---|---|
| OD-05a | Can templates pre-select Sensitive communication permissions, granted only after owner confirmation with step-up? | **Approve** | Before messaging (Phase 10) |
| OD-05b | Does the counterparty see "Sent by an authorized family member" while the owner sees the identity? | **Approve** | Before messaging (Phase 10) |
| OD-05c | Should `manage_family_authorizations` and `manage_verification_submission` become Owner-only? | **Approve** | Before Phase 5 (verification) |
| OD-05d | Is owner approval needed for each document share? | **Approve** | Before documents (Phase 10/11) |
| OD-05e | Do invitations expire after 14 days? | **Approve (14 days, configurable)** | **Now**: see §3 |
| OD-05f | May managers resign? | **Approve** | Low; can follow Phase 4 review |
| TR-16 | What are the step-up windows: 12 h for communication, 10 min for other Sensitive actions, single use for High, all configurable? | **Approve** | **Now**: it blocks every Sensitive manager action |

## 2. OD-05: the questions, alternatives and implications

The A4 proposal (REC-BIZ) is the only alternative written down for each item. The other option is to keep the approved doc 14 §1–§8 baseline as it is.

### OD-05a: template pre-selection of Sensitive communication permissions
- **Proposal:** choosing the Communication or Advanced template *pre-selects* `view_conversations`, `send_messages` and (Advanced) `upload_attachments`. They're granted only when the owner explicitly confirms the Sensitive section with an owner step-up.
- **Alternative (baseline):** templates never include Sensitive permissions in any form. The owner adds them one by one.
- **Implemented today:** templates grant only their Normal permissions. Sensitive permissions are granted individually, with explicit confirmation and an owner step-up. The API lists them separately (`permissions` and `granted_on_apply`). No pre-selection semantics exist.
- **Depends on it:** nothing implemented.
- **If deferred:** the templates work, but the Communication template is less useful until messaging exists. No risk.

### OD-05b: counterparty label for manager-sent content
- **Proposal:** the other party sees "Sent by an authorized family member". The owner sees which manager sent it.
- **Alternative:** show the manager's name, or show no indication at all.
- **Implemented today:** none. Messaging and requests aren't built.
- **If deferred:** this blocks manager messaging and request UX (Phases 9–10), not Phase 4.

### OD-05c: two permissions become Owner-only
- **Proposal:** `manage_family_authorizations` and `manage_verification_submission` become Owner-only. The current doc 14 classifies both as Sensitive.
- **Implemented today:** `manage_family_authorizations` is seeded **inactive**, so it can't be granted and only the owner manages managers. `manage_verification_submission` is active and Sensitive, so it can be granted. Since today's change (TR-02 review), a manager can't *use* any Sensitive permission.
- **If deferred:** decide before Phase 5. Otherwise a manager could later be allowed to submit identity documents for the owner.

### OD-05d: owner approval per document share
- **Proposal:** each `share_documents` action needs the owner's approval (a High-tier action).
- **Implemented today:** none. Documents aren't built.
- **If deferred:** this blocks manager document sharing (Phases 10–11) only.

### OD-05e: invitation TTL (14 days)
- **Proposal:** a PENDING invitation expires after 14 days (doc 15 §4, PENDING → EXPIRED).
- **Implemented today:** no TTL. Invitations stay pending until answered or cancelled, and `invitation_expires_at` is unset.
- **New consequence (KI-34 fix):** an invitation to a number with no eligible account now stays PENDING too, by design, so the owner can't tell the difference. Without a TTL, these invitations stay pending until the owner cancels them, and the invitation list keeps growing. A TTL that applies the **same way** to resolved and unresolved invitations keeps them indistinguishable and keeps the list clean.
- **Recommendation:** approve 14 days, configurable. Both invitation types would expire the same way, through the existing expiry job, and the linked authorization would go PENDING → EXPIRED.

### OD-05f: manager resignation
- **Proposal:** a manager may resign. The authorization goes to REVOKED with reason `RESIGNED`, and the owner is notified.
- **Implemented today:** only the owner can end an authorization. A manager who wants to leave must ask the owner.
- **If deferred:** this is a usability gap, not a security gap: the manager's access ends whenever the owner revokes it.

## 3. TR-16: step-up windows

- **Recommendation (A4 §3, §7.2):**
  - Sensitive communication permissions need a manager re-authentication within the last **12 h**.
  - Other Sensitive permissions need one within **10 min**.
  - High-tier actions need a **single-use** verification for each action (`SensitiveActionVerification`, doc 03 §6.8), consumed in the business transaction.
  - Owner O-tier actions need an owner step-up within 10 min.
  - All windows are configurable.
- **What it governs:** step 10 of the acting-profile algorithm (doc 04 §24.1).
- **Implemented today:**
  - **Grant side:** the owner's step-up when granting Sensitive permissions uses the general step-up window, `AUTH_STEP_UP_WINDOW_SECONDS` = 300 s (TR-01).
  - **Use side:** since the TR-02 review on 2026-11-20 (DR-2026-11-20-C-5), any manager use of a Sensitive permission **fails closed** with `403 sensitive_use_unavailable`. The approved rule requires extra security at use (FR-FAM-005, doc 14), and that mechanism isn't decided. Today the only Sensitive action in the code is a manager changing profile visibility (`manage_privacy_settings`). The owner can always do it.
  - The H tier and `SensitiveActionVerification` aren't built.
- **Depends on it:** nothing that works today. Every Sensitive manager action stays unavailable until TR-16 is decided.
- **If deferred:** managers hold Sensitive permissions they can't use. Later phases are blocked: manager messaging (`send_messages`, `view_conversations`), privacy, block and hide management, and document sharing.
- **Implementation after approval:** a configurable window per class, the check `AuthSession.reauthenticated_at` at use, `403 step_up_required`, and the H-tier model and migration. This is a small change, plus one migration for H.

## 4. Consequences of leaving everything deferred

- Phase 4 stays safe: nothing grants more access than the approved baseline, and Sensitive manager use is blocked.
- FR-FAM-004, FR-FAM-005 and FR-FAM-006 stay IN_PROGRESS in doc 18.
- Phases 5 and 9–11 inherit blockers: OD-05c before verification; OD-05a/b/d and TR-16 before manager messaging and documents.

## 5. Requested owner decisions

1. **TR-16:** approve the windows as proposed (12 h / 10 min / single-use / 10 min owner), all configurable.
2. **OD-05e:** approve a 14-day invitation TTL, applied the same way to every invitation.
3. **OD-05c:** approve making both permissions Owner-only.
4. **OD-05a, b, d, f:** approve as proposed, or defer a, b and d to the messaging and document phases.
