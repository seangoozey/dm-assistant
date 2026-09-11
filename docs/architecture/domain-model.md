# Provisional Domain Model

The model is intentionally provisional until acceptance fixtures validate it.

## Core records

- **Source document:** immutable evidence with path, hash, source time, raw content, and importer version.
- **Import candidate:** a non-canonical, section-aware interpretation linked to immutable source evidence and retained until reviewed or marked source-removed.
- **Record identity:** a thin stable UUID shared by every referenceable family record; it carries no family-specific truth or arbitrary JSON payload.
- **Entity:** a stable subject with one controlled kind: NPC, PC, location, faction, item, event, worldbuilding, or rules element.
- **Plan:** a stable named intention or campaign-development guide with a controlled kind and lifecycle; it is not evidence that an outcome occurred.
- **Alias:** alternate, historical, misspelled, or source-specific name resolving to an entity.
- **Claim:** a meaningful assertion linked to sources, authority, state, visibility, time, and affected entities.
- **Relationship:** a typed connection that can have its own state, authority, time, and provenance.
- **Proposal:** a versioned set of intended mutations.
- **Approval:** authorization for an exact proposal version and scope.
- **Change set:** the mutations applied in one transaction.
- **Receipt:** durable record of input, decision, exact changes, conflicts, and outcome.
- **Workflow session:** Brainstorm, Lore Entry, Real Play, Audio Brainstorm, Session Debrief, or another explicit environment.
- **Derived artifact:** export, transcript correction, index entry, or VTT package created from authoritative records.

## Provisional claim states

The complete atomic `assertion_text` is a claim's authoritative semantic content. `subject_entity_id`, `predicate`, and `object_entity_id` are optional retrieval enrichment and never replace, truncate, or gate promotion of the assertion. When present, a subject is a stable entity identity and enables subject-aware safeguards and traversal.

- `observed`: happened during actual play.
- `established`: accepted background or current fact.
- `intended`: an NPC or faction presently plans or wants this.
- `prepared`: the DM prepared this scenario or material.
- `possible`: an unpromoted possibility.
- `proposed`: awaiting a promotion decision.
- `disputed`: sources conflict.
- `superseded`: previously valid or expected but replaced.
- `rejected`: explicitly declined and retained only for provenance.

Rumor, belief, uncertainty, secrecy, and visibility are separate dimensions rather than claim states.

## Temporal model

Real-world audit instants and in-game campaign chronology are distinct types (ADR-0007).

- `recorded_at`: when the assertion entered the system. A real-world UTC instant (`timestamptz`).
- `effective_from` / `effective_until`: when a state is true in the fiction. Integer campaign dates (`year`, `month`, `day`, `calendar_id`).
- `expected_at`: intended or prepared timing. An integer campaign date.
- `observed_at`: actual-play timing. An integer campaign date; required for an `observed` claim.
- `session_id`: session that introduced or established it.
- Calendar identity: every campaign date carries a `calendar_id` (v1: `gregorian-ce`) backed by a hardcoded calendar spec enabling same-calendar day arithmetic. BCE years are negative integers; cross-calendar ordering is never implicit.

Approximate dates (for example `~290CE`) are preserved as given at promotion time; a structured precision vocabulary is a later version. Legacy relative-year shorthand (`-N`) resolves once against the campaign's explicit anchor year (505CE) and is stored as the resulting absolute year.

## Claim granularity

Do not force every sentence into a subject-predicate-object triple. Preserve prose where decomposition would lose meaning, while extracting structure necessary for retrieval, authority, identity, time, and conflict checks.

## Live sessions and encounters

A live session is the chronological container for table observations; an encounter is prepared material that may be entered, left, or resumed. They are independent many-to-many contexts (ADR-0013). A session note may have no encounter context or may identify an encounter and section. Closing a session never establishes encounter completion, and encountering a section never proves its prepared outcome occurred. Mutable resume state supports running the game, while the assembled immutable session note supplies evidence for observed claims.

## Stable identity

File paths and names are aliases, not primary identity. Entity IDs remain stable across renames and source moves. Similar names must not merge automatically without sufficient evidence.

## Kinds and tags

Record families and their kinds are separate namespaces. Registry metadata owns stable identity, versioned keys, documentation, aliases, deprecation, and replacement. Code and migrations own executable behavior. Unsupported kinds fail into review; they do not become `other` or silently fall back to worldbuilding.

Tags are optional non-exclusive retrieval facets. They do not establish truth, replace an entity kind, encode a date, or identify source-versus-artifact status. A disputed descriptor requires a sourced claim. PC and NPC kinds encode a permanent agency boundary: only the player controls a PC, only the DM controls an NPC, and no planning record predicts a PC action.

PC and NPC document profiles present `race`, `sex`, and intact background as distinct character information; PC profiles additionally present the player. A missing profile value remains explicitly unrecorded rather than inferred. For the curated PC sources, `Canon Summary`, `Background / History`, `Relationships`, and `Current Status` are derived navigation material rather than independent evidence. The original player biography supplies background, session notes supply real-play facts, attributed player statements supply player plans, and private GM notes remain conditional DM plans.

## Plans and agency

Plan kinds are `campaign_direction`, `in_world_plan`, and `player_plan`. Campaign direction is ownerless DM guidance. An in-world plan is owned by an NPC or faction. A player plan records only an attributed, time-bound statement about a PC and remains revocable and nonbinding. None of these predicts a PC action.

Plan lifecycle is `active`, `completed`, `failed`, `abandoned`, or `superseded`. Completion and failure require separate observed claims. Plan relationships, source evidence, lifecycle events, and their receipts preserve provenance without moving truth state onto the plan.
