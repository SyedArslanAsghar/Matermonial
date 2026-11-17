# ADR-028: Transactional outbox as a pseudonymous work queue

**Status:** PROPOSED (TR-11). ADR decision and TR-11 approval are both due before G4 (baseline v4.6 approval-by-gate table). Refines ADR-014, whose **core** decision (outbox events written in the same transaction as the business operation and processed asynchronously with retryable, idempotent delivery) is APPROVED (FR-NOT-005; DR-2026-11-17-C2). Only the refinements described in this ADR are PROPOSED; the approved core doesn't make them approved.
**Date:** 2026-11-16 (G1)
**Source:** approved baseline `docs/baseline/v4.6-F3/` (DR-2026-11-16-1). Approving the baseline didn't approve this ADR's technical content unless the status above says so.

## Context

Notifications and financial obligations must not be lost when a transaction commits but a later step fails, and the queue must not undermine log pseudonymisation or deletion.

## Decision

`OutboxEvent` in `common/events` is a mutable queue with pseudonymous recipients, an HMAC dedupe key and a payload encrypted with a rotating queue key. Processing is two-phase (short lease claim, then a handler transaction that marks its own event DONE as its last lock). Financial events are wake-up signals only; obligations are always re-derivable from domain records.

## Consequences

- Queue-key destruction has strict preconditions.
- Undecryptable financial events follow a two-stage resolution.

## Where specified

doc 03 §22.12; doc 12 §6; doc 05 §25.6; doc 09 §19.9

## Related corrections

DCR-22, DCR-68, DCR-73, DCR-84, DCR-98 (doc 20)
