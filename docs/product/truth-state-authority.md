# Truth States and Authority Decision Table

This specification turns the product invariants into deterministic Campaign Core behavior. It governs individual claims and relationships; source documents remain immutable evidence rather than truth-state containers.

## Independent dimensions

Every claim records separate values for state, authority, confidence, visibility, time, and provenance. No value is inferred from a file path alone after import.

| Dimension | Meaning | Examples |
| --- | --- | --- |
| State | The claim's lifecycle and present truth role. | `observed`, `established`, `intended`, `prepared` |
| Authority | Why the claim may affect campaign truth. | real play, explicit correction, explicit lore |
| Confidence | Certainty of extraction or identity resolution, not authority. | confirmed, ambiguous |
| Visibility | Who may retrieve the claim. | DM, party, character |
| Time | Recorded, effective, expected, and observed dates/ranges. | `expected_at`, `observed_at` |
| Provenance | Immutable supporting source and extraction details. | source hash, excerpt, actor, receipt |

Rumor, belief, secrecy, and uncertainty are epistemic or visibility attributes, not replacements for a lifecycle state.

## Claim-state transitions

| State | Entry rule | Exit rule | Supersession rule |
| --- | --- | --- | --- |
| `observed` | An unambiguous real-play observation is accepted. | It may be disputed by a later conflicting authoritative record or corrected explicitly. | A later explicit correction may supersede it only through a reviewed retcon resolution; preparation never supersedes it. |
| `established` | Explicit, unambiguous lore is applied without material conflict, or an approved proposal is promoted. | A conflict creates a review item; a correction or approved replacement resolves it. | Replaced claim becomes `superseded` only with an explicit correction or reviewed resolution. |
| `intended` | Explicit NPC or faction current plan, desire, or objective is recorded. | It ends when observed play establishes completion, failure, abandonment, or a changed intention. | The former intention becomes `superseded`; a disrupted plan also receives a failed-plan review item. It never establishes its outcome. |
| `prepared` | DM preparation or an encounter scenario is captured. | It is retained as preparation, altered, rejected, or displaced by actual play. | Conflicting observed play automatically supersedes it for what occurred; the preparation remains preserved. |
| `possible` | A brainstorm idea or unconfirmed branch is captured. | It is revised, rejected, or converted into a versioned proposal. | A later working idea may link to it as a replacement, but it remains non-canon. |
| `proposed` | A concrete versioned mutation is synthesized from a workflow. | It is approved and applied, edited into a new version, rejected, or deferred. | Editing creates a new immutable version and invalidates approval of the changed version. |
| `disputed` | Conflicting claims cannot be resolved by an automatic authority rule. | An explicit correction or reviewed resolution selects the result. | The losing claim is preserved as `superseded` or remains disputed when no conclusion is made. |
| `superseded` | A formerly valid claim is displaced according to this table. | It remains historical provenance; it is not silently deleted. | It can only be superseded again by a later explicit resolution that corrects the history of the replacement. |
| `rejected` | A DM explicitly declines a possibility or proposal. | It remains auditable and excluded from normal retrieval. | A later, separately captured idea may be linked to it; rejection does not erase source history. |

Relationships use the same state, authority, time, provenance, and conflict rules as claims.

## Authority and conflict rules

The following outcomes apply when a new claim materially conflicts with an existing claim about the same subject, predicate, time, and relevant visibility. Identity ambiguity prevents automatic application in every row.

| Incoming source category | Normal state | Compared with | Required outcome | Automatic? |
| --- | --- | --- | --- | --- |
| Real-play observation | `observed` | `prepared` | Record the observation; supersede only the prepared outcome for the occurrence; retain preparation and issue a receipt. | Yes |
| Real-play observation | `observed` | `intended` | Record what occurred; mark the intention completed, failed, or needing review based only on the observation. Do not invent a reaction. | Yes when unambiguous |
| Real-play observation | `observed` | `established` or prior `observed` | Create a possible-retcon comparison containing both sources, downstream effects, and interpretations; no canonical overwrite. | No |
| Explicit DM correction | `established` or `observed` as specified by the correction | Any conflicting state | Require an explicit target/scope when ambiguity remains; apply the reviewed correction, supersede displaced claims, and issue a retcon receipt. | Only when target and scope are unambiguous |
| Explicit lore entry | `established` | Non-conflicting evidence | Apply with a receipt. | Yes |
| Explicit lore entry | `established` | `prepared`, `possible`, or `proposed` | Apply lore; leave non-canon material preserved and annotate its conflict where useful. | Yes |
| Explicit lore entry | `established` | `established` or `observed` | Present a conflict or possible-retcon comparison. | No |
| NPC or faction plan | `intended` | Any outcome claim | Store only the present intention and conditions. | Yes if unambiguous |
| Preparation or encounter design | `prepared` | Any canonical claim | Preserve as a scenario; flag contradiction but do not alter canon. | Yes if identity is clear |
| Brainstorm content | `possible` | Any canonical claim | Preserve outside canon and show evidence/conflicts. Promotion requires exact versioned approval. | Capture only |
| Unclassified import | no canonical state | Any | Quarantine for review; retain raw source and import receipt. | Yes, to quarantine only |
| Derived artifact or provider transcript | derived only | Any | Link provenance and require review or a selected workflow before creating a claim. | Never as a direct canonical write |

## Approval and mutation rules

1. Every proposal has an immutable ID, version, exact mutation list, and scope.
2. Inspecting, creating, or editing one proposal item never approves any item.
3. Approval binds only to the displayed proposal ID, version, and selected scope. A changed proposal produces a new version.
4. Promotion runs as one idempotent Campaign Core transaction: validate approval, apply all scoped mutations or none, then write the receipt.
5. A direct Lore Entry operation inside a Brainstorm creates its own change set and receipt, then returns to the still-pending brainstorm.

## PC agency and intentions

| Input type | Stored representation | Prohibited representation |
| --- | --- | --- |
| DM hope, theme, pressure, or desired PC arc | DM-only `prepared` or `possible` campaign direction, with conditional wording. | An `established` claim that the PC will choose, intend, or accomplish it. |
| A PC action during play | `observed` action with session provenance. | Backdating a planned action as observed. |
| DM statement of an already-established PC fact | `established` fact with explicit source. | Inferring future PC behavior from the fact. |

NPC and faction intentions are current facts about the NPC or faction, but never proof that the intended event occurred. When play disrupts an intention, the system records only the observed disruption and queues review of the failed plan.

## Time rules

| Situation | Required records | Result |
| --- | --- | --- |
| A prepared or intended event has a target date | `expected_at`, precision, and source. | The date is an expectation, not an occurrence. |
| Play establishes the event on the expected date | Preserve `expected_at`; add `observed_at` and an `observed` claim. | Actual occurrence is authoritative. |
| Play establishes it at a different date | Preserve the original expected date and source; add actual `observed_at`. | Observed date governs chronology; earlier expectation is provenance. |
| The target date passes without play evidence | Retain the expected claim; do not infer failure or occurrence. | Create review only when the workflow or DM asks to resolve it. |
| A date conflicts with established history | Preserve both sources and require a timing/retcon comparison. | No automatic overwrite. |

## Fixture-derived acceptance examples

The cases in `tests/fixtures/interaction_cases.yaml` are direct test translations of this specification:

| Fixture | Rule exercised |
| --- | --- |
| `inspect-one-pending-claim-does-not-promote-siblings` | approval scope |
| `invented-npc-lore-is-rejected` | records-clerk boundary |
| `explicit-read-aloud-permission-is-bounded` | derived creative artifact boundary |
| `direct-lore-update-returns-to-brainstorm` | nested scoped mutation |
| `edited-claim-requires-exact-version-promotion` | version invalidation and idempotency |
| `pc-directions-are-not-predicted-actions` | PC agency |
| `unknown-noble-name-remains-unknown` | grounded unknown answer |
| `real-play-overrides-prepared-outcomes` | observed versus prepared precedence |
| `audio-later-withdrawal-supersedes-earlier-candidate` | non-canon candidate revision |
