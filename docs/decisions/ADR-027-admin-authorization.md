# ADR-027: Administrative authorization from a single source

**Status:** APPROVED (DR-2026-11-18-G4, 2026-11-18; with TR-07). Implemented as decision D-4 Option A′: `PermissionsMixin` kept; Django groups and `user_permissions` link tables stay empty, enforced by trigger and test. *Previously:* PROPOSED (TR-07). ADR decision and TR-07 approval are both due before G4 (baseline v4.6 approval-by-gate table).
**Date:** 2026-11-16 (G1)
**Source:** approved baseline `docs/baseline/v4.6-F3/` (DR-2026-11-16-1). Approving the baseline didn't approve this ADR's technical content unless the status above says so.

## Context

Doc 03 defines AdminRole tables, while an earlier proposal used Django Groups. Two independently editable sources of truth would conflict (contradiction C-14).

## Decision

Django Admin with MFA (django-otp). The `AdminRole` / `AdminPermission` / `AdminRolePermission` / `AdminUserRole` tables are the only source of administrative authorization, read by a custom authentication backend. Django Groups and `user_permissions` aren't used. `is_staff` is a projection; `is_superuser` is break-glass only.

## Consequences

- No SQLAdmin.
- Admin forms can't edit `is_staff`, `is_superuser`, groups or permissions directly.

## Where specified

doc 03 §22.15; doc 02 §12

## Related corrections

DCR-03, DCR-44 (doc 20)
