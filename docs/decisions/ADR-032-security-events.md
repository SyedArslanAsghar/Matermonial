# ADR-032: Security-event model and log pseudonymisation

**Status:** APPROVED (DR-2026-11-18-G4, 2026-11-18; with TR-17 and TR-23). *Previously:* PROPOSED (TR-17, TR-23). ADR decision and TR approvals are due before G4 (baseline v4.6 approval-by-gate table). Relates to ADR-022, whose status is still "Recommended" (decision due before G4).
**Date:** 2026-11-16 (G1)
**Source:** approved baseline `docs/baseline/v4.6-F3/` (DR-2026-11-16-1). Approving the baseline didn't approve this ADR's technical content unless the status above says so.

## Context

Login and security history must be kept separately from session state, manager logs and the general audit log, and must survive account deletion without staying identifiable.

## Decision

`AccountSecurityEvent` is an append-only, partitioned event log with a defined taxonomy. AuditLog and AccountSecurityEvent store pseudonyms and per-subject encrypted envelopes; anonymisation unlinks the pseudonym and destroys the subject key without modifying log rows. An external compliance registry keeps deletion and shred decisions authoritative across restores.

## Consequences

- Partition-level retention; holds defer anonymisation.
- Pseudonymous grouping after unlinking needs legal review (R-19).

## Where specified

doc 06 §22.3, §22.6–§22.7; doc 03 §22.2, §22.15; doc 09 §19

## Related corrections

DCR-35, DCR-60, DCR-67, DCR-74, DCR-75, DCR-76, DCR-86 (doc 20)
