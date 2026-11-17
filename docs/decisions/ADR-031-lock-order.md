# ADR-031: Global lock-order and anchor policy

**Status:** PROPOSED (TR-09, TR-22). TR-09 / TR-22 policy approval due before G3 (doc 19); ADR decision due before G4 (baseline v4.6 approval-by-gate table).
**Date:** 2026-11-16 (G1)
**Source:** approved baseline `docs/baseline/v4.6-F3/` (DR-2026-11-16-1). Approving the baseline didn't approve this ADR's technical content unless the status above says so.

## Context

Many services lock accounts, profiles, pairs, wallets and domain rows together. Without one order, deadlocks and races are likely (contradictions C-19…C-32).

## Decision

One global lock order (authorization → account → profile → pair advisory locks → wallet → allowances → domain rows → inserts → own outbox row), at most one exclusive state anchor per transaction, protective actions that never depend on the counterparty, whole-transaction retry on deadlock or serialization failure, per-service `LOCK_PLAN`s and an implicit foreign-key lock inventory.

## Consequences

- The tracker sees only explicit locks; implicit locks are covered by design and PostgreSQL concurrency tests.

## Where specified

doc 12 §5

## Related corrections

DCR-42, DCR-50, DCR-53, DCR-63, DCR-81, DCR-82 (doc 20)
