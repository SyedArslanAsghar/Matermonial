# ADR-026: Acting-profile authorization (ActorContext)

**Status:** DIRECTION ADOPTED (DR-2026-11-18-G4, 2026-11-18). TR-02 itself stays PROPOSED and is decided and implemented at G5 Phase 4. *Previously:* PROPOSED (TR-02). ADR decision due before G4 (baseline v4.6 approval-by-gate table); TR-02 approval due G4 / Phase 4 (doc 19).
**Date:** 2026-11-16 (G1)
**Source:** approved baseline `docs/baseline/v4.6-F3/` (DR-2026-11-16-1). Approving the baseline didn't approve this ADR's technical content unless the status above says so.

## Context

Managers act for profiles they don't own. A profile ID supplied by the client must never establish authorization (CC-R45).

## Decision

Every profile-scoped request runs a 17-step ordered algorithm that authenticates the account, selects the profile (`X-Acting-Profile` only selects, never proves), checks ownership or an ACTIVE, unexpired authorization, the owner's account standing, the permission tier and step-up, resource participation and eligibility, then builds an immutable `ActorContext` whose billing account is always the represented profile's owner.

## Consequences

- Uniform 404 responses avoid disclosing other profiles.
- Delegated writes re-verify the authorization row under `FOR SHARE`.

## Where specified

doc 04 §24.1

## Related corrections

DCR-17 (doc 20)
