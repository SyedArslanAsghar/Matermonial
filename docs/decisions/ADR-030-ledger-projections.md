# ADR-030: Ledger as the permanent record; balances as projections

**Status:** DIRECTION ADOPTED (DR-2026-11-18-G4, 2026-11-18). TR-15 itself stays PROPOSED and is decided and implemented at G5 Phase 7 / 9. *Previously:* PROPOSED (TR-15). ADR decision due before G4 (baseline v4.6 approval-by-gate table); TR-15 approval due Phase 7 / 9 (doc 19).
**Date:** 2026-11-16 (G1)
**Source:** approved baseline `docs/baseline/v4.6-F3/` (DR-2026-11-16-1). Approving the baseline didn't approve this ADR's technical content unless the status above says so.

## Context

Credit balances must never go negative, buckets must stay separate, and history must be permanent [DECIDED].

## Decision

The append-only ledger (`CreditOperation` + `CreditTransaction`) is the record. Wallet purchased buckets and per-allowance remaining amounts are projections updated only in the same transaction as the ledger row. Refunds use `CreditRefundOperation` / `CreditRefundLine` with composite-FK integrity. Nightly reconciliation reports discrepancies and never fixes them automatically.

## Consequences

- Corrections are compensating ADJUSTMENT operations under dual approval.
- Wallet closure at deletion keeps balances (OD-07g OPEN).

## Where specified

doc 03 §22.1, §22.11; doc 05 §25.3, §25.7

## Related corrections

DCR-31, DCR-56, DCR-65, DCR-69, DCR-70, DCR-71, DCR-77, DCR-78 (doc 20)
