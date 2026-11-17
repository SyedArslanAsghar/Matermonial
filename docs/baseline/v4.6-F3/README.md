# Matermonial Documentation Baseline v4–v4.6-F3: Manifest

**Status:** APPROVED baseline (DR-2026-11-16-1), preserved under DR-2026-11-16-P4
**Created:** 2026-11-16, G1 step 1
**Rule:** The files listed below are **read-only**. Any change needs a new decision record in `docs/decisions/new_architecture_decisions.md`.

## Scope

`approved/` contains v4–v4.6-F3. These eleven packages are the **approved documentation baseline** (DR-2026-11-16-1). Approving the baseline approves DCR-01…DCR-99 as the basis for documentation changes. It does not approve the proposed technical recommendations (TR) or business recommendations (REC-BIZ) inside them.

`referenced/` contains A1–A4 (DR-2026-11-16-P1):
- **A1** is historical assessment and context.
- **A2–A4** are incorporated by reference **only** where an approved package explicitly cites one of their sections.

A1–A4 are not an approved baseline or approved requirements on their own. Content that a later package superseded must never be restored. Proposed TRs stay PROPOSED, and OPEN business decisions stay OPEN.

**Where packages disagree, the later package wins.** Read the approved packages in numeric order (01 → 11).

## Source and extraction method

- **Source:** Claude Code session transcript, session `5b02b07d-8604-414d-a821-668198cd3b4b`. An offline backup is confirmed by the project owner (DR-2026-11-16-G1).
- **Method:** a script outside the repository selected each assistant message by its exact timestamp and opening text, and wrote the message text byte for byte as UTF-8. Nothing was retyped, reformatted or merged.
- **Checks on every file:**
  - each source message was fully generated (`stop_reason = end_turn`)
  - SHA-256 of the source text equals the hash expected from the G1 preparation inventory
  - SHA-256 of the written file equals SHA-256 of the source text
  - read-back checks of the first heading and the final line
- **Result:** 15 of 15 files matched. No mismatch.

## Files

| File | Package | Source timestamp (UTC) | Bytes | SHA-256 |
|---|---|---|---|---|
| `approved/01_v4.md` | v4 | 2026-11-16T12:11:50 | 76644 | `90a740bedef9a4c9815995bdecbf3764b595e58724257919263c59757584c2c6` |
| `approved/02_v4.1.md` | v4.1 | 2026-11-16T12:41:48 | 26661 | `2f6206886cf6ef80a6519aacf722f08688c665f701a8bf243a7cac7bb66b69a8` |
| `approved/03_v4.2.md` | v4.2 | 2026-11-16T12:51:11 | 29391 | `661cf74557f75812cbec3e89b50e82873cb626da359bd072f31603d185429410` |
| `approved/04_v4.3.md` | v4.3 | 2026-11-16T12:56:37 | 28665 | `28eb8c1321aea947a63858e618160e232d44e1b9a1ea619a0b9d658c20193816` |
| `approved/05_v4.4.md` | v4.4 | 2026-11-16T13:03:48 | 26857 | `12fe9e7adbd8a503ebe9ad9c98966131fccb48cd378e30c2d2d9f25bfa294df5` |
| `approved/06_v4.5.md` | v4.5 | 2026-11-16T13:10:15 | 33334 | `3b115f874754acb00a50bc3751e3d420403d16a4ebf8f79b7eb958a63814f944` |
| `approved/07_v4.6.md` | v4.6 | 2026-11-16T13:16:53 | 30734 | `f9da3988e4c1fdadc3543ba7d2b7dd669fc5b77b537b870dff55416518a840bb` |
| `approved/08_v4.6-F.md` | v4.6-F | 2026-11-16T13:26:06 | 32874 | `bea7683aa3173e225a1821f7fd9f3b42252e61412b470849a80c8d6350b0800a` |
| `approved/09_v4.6-F1.md` | v4.6-F1 | 2026-11-16T13:33:54 | 22032 | `7adbed6f328a689f5a208144c9214a4c4ef8ab57cfdb887d31d253fca40c3cc5` |
| `approved/10_v4.6-F2.md` | v4.6-F2 | 2026-11-16T13:38:30 | 14264 | `20e0dca9cd62f44ef1d6371487797f56b0dd09d0d6c19005d3b91eb4d83f7304` |
| `approved/11_v4.6-F3.md` | v4.6-F3 | 2026-11-16T13:43:28 | 12268 | `3a35e06710e2e251390cf02ab505f4ff59ddcb0d5636750b1f7416f0e8e09c05` |
| `referenced/A1_assessment.md` | A1: Project Assessment Report | 2026-11-16T10:15:17 | 41708 | `ec8f820f6d86aac4f9d4fbfbde8c16ec8b8ad7058e1a7a2897d1fa428bf4d9df` |
| `referenced/A2_v1.md` | A2: Reconciliation Package v1 | 2026-11-16T10:36:38 | 66950 | `b56c4b2442cb5469cb78bf5f7b03d438e2572dd877dc5b5c8777cba08fe7ef95` |
| `referenced/A3_v2.md` | A3: Reconciliation Package v2 | 2026-11-16T10:48:03 | 50345 | `330e146262dc0c69c865844fca6576e9f2698a16513ee15c42391214b06fe19a` |
| `referenced/A4_v3.md` | A4: Reconciliation Package v3 | 2026-11-16T10:58:41 | 55648 | `6a9c227379ba54445fb308198906c7d4c6e9039f5fc5643c08dab06c999e17fd` |

To verify, run `sha256sum -c SHA256SUMS` in this folder.

## Notes on reading the packages

- The packages are written in the response style of the review session. They contain conversational lines (for example "I'm waiting for your approval") that record the review history and aren't specification text.
- `approved/11_v4.6-F3.md` begins with a note that the reviewer's request was cut off, and records the interpretation used for test T-REG-054.
- Pre-G1 copies of `CLAUDE.md`, `README.md` (under `root/`) and `docs/handover/00`–`17` are in `docs/baseline/pre-g1-snapshot/`, for rollback while the project has no Git history.
