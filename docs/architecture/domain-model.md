# Provisional Domain Model

The model is intentionally provisional until acceptance fixtures validate it.

## Core records

- **Source document:** immutable evidence with path, hash, source time, raw content, and importer version.
- **Entity:** NPC, PC, location, faction, item, cosmological concept, encounter, session, or other stable subject.
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

- `recorded_at`: when the assertion entered the system.
- `effective_from` / `effective_until`: when a state is true.
- `expected_at`: intended or prepared timing.
- `observed_at`: actual-play timing.
- `session_id`: session that introduced or established it.
- `precision`: exact, approximate, relative, or unknown.

## Claim granularity

Do not force every sentence into a subject-predicate-object triple. Preserve prose where decomposition would lose meaning, while extracting structure necessary for retrieval, authority, identity, time, and conflict checks.

## Stable identity

File paths and names are aliases, not primary identity. Entity IDs remain stable across renames and source moves. Similar names must not merge automatically without sufficient evidence.
