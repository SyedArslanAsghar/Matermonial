# ADR-025: Authentication sessions and tokens

**Status:** PROPOSED (TR-01). ADR decision and TR-01 approval are both due before G4 (baseline v4.6 approval-by-gate table).
**Date:** 2026-11-16 (G1)
**Source:** approved baseline `docs/baseline/v4.6-F3/` (DR-2026-11-16-1). Approving the baseline didn't approve this ADR's technical content unless the status above says so.

## Context

The SRS requires secure login and logout, session and token revocation, session and device history, and abuse protection (FR-007, FR-ACC-005). Web and mobile clients need different mechanisms.

## Decision

Web uses Django server-side sessions linked one way to an `AuthSession` record (no Django session key stored). Mobile uses opaque, hashed access and refresh tokens with deterministic, idempotent refresh rotation and a 15-second grace for lost responses. Lifetimes, `__Host-` cookie rules, replay-detection limits, K_rot key management and the auth-flow lock order are specified.

## Consequences

- Revocation takes effect on the next request through the session status check.
- The refresh grace adds a small, documented replay window (risk R-13).
- K_rot needs secret-store storage and rotation and compromise procedures.

## Where specified

doc 06 §22.1–§22.2; doc 03 §22.2; doc 12 §5

## Related corrections

DCR-16, DCR-25, DCR-52, DCR-54 (doc 20)
