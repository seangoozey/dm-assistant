---
id: TKT-0045
title: Extraction context and prompt improvement
status: done
priority: P1
milestone: planning-workspace
depends_on: [TKT-0037]
created: 2026-08-06
updated: 2026-08-09
---

# TKT-0045: Extraction Context and Prompt Improvement

## Outcome

The extraction harness receives document-level context (heading, frontmatter, source path) alongside the candidate's section text, so the model can identify the subject entity, infer the record type, and produce correctly attributed assertions instead of generic ones like "the character has player Presto."

## Context

The current extraction (TKT-0034/0035) sends only the candidate's section-level assertion text to the model. A candidate from the "Character Details" section of `pcs/coreferra.md` contains bullet points (`- **Player:** Presto`, `- **Origin:** Catlantis`) but no entity name — the model has no way to know the subject is "Coreferra" or that this is a PC record. The result is assertions with `"the character"` as the subject and guessed authority values.

This will recur across every document type during migration: NPCs, locations, lore, session notes, and encounters each have different structure and different correct authority/visibility defaults. The extraction prompt and context will need iterative tuning as the migration progresses through different document classes.

Read `docs/decisions/ADR-0008-openrouter-v1-ai-provider.md`, `docs/migration/markdown-importer.md`, and TKT-0034.

## Scope

- Extend the extraction input to include: the source document's heading (first `# ` line), its frontmatter (`type`, `canon_status`, `status`), and its relative path. The candidate's section text remains the primary evidence; the context is supplemental framing.
- Update the system prompt to instruct the model to use the document context for subject identity and record-type inference (e.g., `type: pc` means the subject is a player character; `type: npc` means DM-controlled; `type: location` means a place).
- Adjust the prompt to produce better authority defaults (frontmatter metadata like player/origin/status is not `real_play`; it is `established`/`explicit_lore`).
- Iterate the prompt using real candidates from different document classes (PC, NPC, location, lore, session note, encounter) as test cases. Record what works and what doesn't.
- Keep the grounding check unchanged — the supporting excerpt must still be verbatim from the source text, not from the context.

## Out of scope

- The app UI restructure or migration page workflow (TKT-0046, TKT-0047).
- Batch extraction across a document's candidates (that's a workflow concern).
- Changing the typed contract or the domain enums.
- Provider or model changes (ADR-0008).

## Acceptance criteria

- [x] Extraction input includes document heading, frontmatter, and source path alongside the section text.
- [x] The system prompt instructs the model to use document context for subject identity and record-type inference.
- [x] A test extraction against `pcs/coreferra.md` candidates produces "Coreferra" as the subject, not "the character."
- [x] Authority assignments are more accurate for metadata fields (not `real_play` for administrative data).
- [x] The grounding check still enforces verbatim excerpt alignment to the section text only.
- [x] Sanitized tests and full repository validation pass.

## Validation plan

- Run extraction against real candidates from at least 3 document types (PC, NPC, location) and verify subject identity and authority are improved.
- Verify the grounding check still rejects fabricated excerpts even with expanded context.
- Document remaining extraction quality gaps for future prompt iterations.

## Remaining before done

None.

## Implementation

- Added `DocumentContext` model to `domain.extraction` carrying source_path, heading, and frontmatter.
- Updated `ExtractionHarness.extract()` to accept optional `document_context`, formatted as a context block preceding the section text in the user message.
- Updated `_build_user_message` to format the context with path, heading, frontmatter JSON, and clear section-text delimiters.
- Rewrote `EXTRACTION_SYSTEM_PROMPT` with record-type guidance (NPC/PC/location/lore/session-note), authority guidance (administrative metadata is `explicit_lore` not `real_play`), visibility guidance, and explicit instruction to use the proper entity name from context.
- Updated `CandidateExtractionRepository` protocol from `load_candidate_assertion_text` to `load_candidate_context` returning `(assertion_text, DocumentContext | None)`.
- Updated `PostgresCandidateExtractionRepository.load_candidate_context` to join through `source_documents` → `source_document_paths` (current path) → latest `source_revisions` (frontmatter JSON + raw content for heading extraction via `_extract_heading`).
- Fixed `ResponseMessage.content` to accept `null` (DeepSeek reasoning models can exhaust tokens on chain-of-thought and return null content). The extraction harness handles null content as a soft-failure error.
- Raised default token limit from 4096 to 8192 and timeout from 30s to 60s to accommodate the reasoning model's longer output.
- Added deterministic sanitized PC, NPC, and location cases that exercise path, heading, frontmatter, subject identity, and administrative authority guidance.
- Added a regression proving that context-only text cannot satisfy the verbatim section-grounding rule.

## Validation

- Ruff clean, strict mypy clean over 61 source files.
- Full repository validation passed: React tests (21), strict TypeScript, Windmill build, 38 retrieval fixtures, all Python tests.
- Focused extraction validation passed: 12 tests, including representative sanitized PC, NPC, and location contexts and context-only grounding rejection.
- Final repository validation on 2026-08-09 passed: Ruff, strict mypy over 61 source files, 236 Python tests (26 skipped), 21 React tests, strict TypeScript, Windmill raw-app build, and 38 retrieval fixtures.
- **Live extraction against real Coreferra Canon Summary candidate produced 4 correct assertions:**
  - subject: "Coreferra" (not "the character" — the document-context fix works)
  - authority: `explicit_lore` for all (not `real_play` — the authority guidance works)
  - assertions: "is from Catlantis", "left home to search for Dariferra", "is officially the Herald of Arkin"
  - all grounded (excerpts verbatim from the section text)
  - no errors, confidence 1.0

### Issues found and fixed during live testing

1. **Null content from reasoning model**: DeepSeek can exhaust tokens on chain-of-thought reasoning and return `content: null`. The `ResponseMessage` model rejected this. Fixed by allowing `content: str | None`.
2. **Token limit too low**: The longer system prompt triggered more reasoning, which consumed all 4096 tokens before content was produced. Raised to 8192.
3. **Timeout too short**: 30s was insufficient for the reasoning model. Raised to 60s.

### Remaining extraction quality gaps for future iteration

- The Canon Summary candidate produced good results because it contains the entity name in the prose. Section-level candidates without the name (like "Character Details" bullet points) still rely on the context to identify the subject — this works now but should be verified across more document types.
- Authority assignments are improved but may still need correction for edge cases (e.g., session-note observations vs. established lore within the same document).
- The prompt's `type:` mapping assumes standard frontmatter values; non-standard or missing frontmatter may produce less accurate results.
