# ADR-029: Three independent status dimensions

**Status:** PROPOSED (the ADR document; DR-2026-11-17-C6). ADR decision due before G4 (baseline v4.6 approval-by-gate table). The decision it records, TR-14 / DCR-12, is **APPROVED** by DR-2026-11-16-2 and is already binding through doc 00 §9.1 and `CLAUDE.md` CC-R69–CC-R70; approving TR-14 didn't by itself approve this ADR document.
**Date:** 2026-11-16 (G1)
**Source:** approved baseline `docs/baseline/v4.6-F3/` (DR-2026-11-16-1). Approving the baseline didn't approve this ADR's technical content unless the status above says so.

## Context

One status vocabulary was used for documents, requirements and implementation, so "APPROVED" meant different things (contradiction C-12).

## Decision

Document status, requirement approval status and implementation status are separate dimensions with defined values, assigners and evidence. `ACCEPTED` replaces implementation `APPROVED` and is set only by the project owner personally (not delegable). Claude Code never sets REVIEWED or ACCEPTED.

## Consequences

- No implementation status beyond PLANNED unless the requirement is APPROVED.

## Where specified

doc 00 §9; `CLAUDE.md` CC-R69–CC-R70

## Related corrections

DCR-12 (doc 20)
