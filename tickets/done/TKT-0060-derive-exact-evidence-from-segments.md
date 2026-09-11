---
id: TKT-0060
title: Derive exact extraction evidence from source segments
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0059]
created: 2026-08-10
updated: 2026-08-10
---

# TKT-0060: Derive Exact Extraction Evidence from Source Segments

## Outcome

The model identifies evidence; Campaign Core copies and stores the exact source text. Verbatim transcription is no longer an unreliable model responsibility.

## Acceptance criteria

- [x] A strong quote match remains the preferred evidence resolution.
- [x] Otherwise, valid claim and coverage segment references resolve the evidence.
- [x] Campaign Core replaces provider excerpt text with exact source segment text.
- [x] Unknown or absent source references remain rejected.
- [x] Reference fallback requires meaningful content-word overlap and cannot legitimize unrelated evidence.
- [x] Coverage indexes remain deterministically reconciled.
- [x] Extractor version is `extraction/6`; tests and validation pass.

## Validation evidence

- Focused extraction and safety tests: 42 passed, including relevant paraphrase recovery, unrelated/context-only evidence rejection, and unknown-reference rejection.
- Repository validation: 255 Python tests passed, 26 skipped; 27 React tests passed; lint, types, policies, build, and retrieval corpus passed.
- Local Campaign Core image rebuilt and both service health checks passed.
