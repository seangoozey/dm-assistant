"""Identity review queue: derived gaps, human decisions, receipts (TKT-0106).

The miner is pure and deterministic — no provider calls, no writes. Detection
and ranking are programmatic; every canonical change is an explicit DM decision
with a receipt. Similar surfaces never merge automatically.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain import EntityKind

QUEUE_NAMESPACE = "identity_queue"
CONNECTORS = {"of", "the", "de", "le", "la", "von", "van"}
# Generic organizational nouns: sharing one of these does not relate two
# surfaces ("Silver Cloaks" vs "White Cloaks" are different orders), while
# sharing a distinctive word does ("Church of Malygos" / "Cult of Malygos").
COMMON_TAIL_WORDS = {
    "cloaks", "guild", "church", "council", "watch", "order", "court",
    "guard", "legion", "brigade", "company", "patrol", "sect", "temple",
    "kingdom", "king", "queen", "lord", "lady", "knights", "priests",
}
# Person-title prefixes: they mark a role, not the person's name. A surface
# starting with one suggests a canonical name without it ("King Peter le
# Fleur" → create as "Peter le Fleur", keeping the full form as an alias).
TITLE_PREFIX_WORDS = {
    "king", "queen", "lord", "lady", "prince", "princess", "duke", "duchess",
    "count", "countess", "baron", "baroness", "earl", "sir", "dame",
    "captain", "sergeant", "bishop", "archbishop", "father", "mother",
    "brother", "sister", "magistrate", "inquisitor", "grand", "high",
}
KIND_TAIL_WORDS = {
    "faction": COMMON_TAIL_WORDS - {"kingdom", "king", "queen", "lord", "lady"},
    "location": {
        "tower", "castle", "city", "camp", "isle", "island", "mountain",
        "range", "temple", "monastery", "manor", "house", "keep", "forest",
        "river", "bridge", "pass", "bay", "harbor", "library", "estate",
        "tavern", "inn", "road", "channel", "village", "town", "hold",
        "chamber", "corridor", "vault", "perch",
    },
    "worldbuilding": {
        "plane", "realm", "leylines", "leyline", "magic", "twilight", "age",
        "era", "pantheon", "calendar", "confluence", "summoning",
    },
}
NON_NAMES = {
    "the", "a", "an", "he", "she", "it", "they", "we", "his", "her", "its",
    "their", "status", "location", "affiliation", "disposition", "appearance",
    "personality", "background", "abilities", "powers", "relationships",
    "current", "date", "time", "place", "purpose", "description", "event",
    "consequence", "section", "notes", "chapter", "scene", "floor", "tower",
    "city", "camp", "key", "lessons", "running", "early", "life", "pre",
    "post", "party", "players", "first", "second", "third", "final", "initial",
    "each", "if", "when", "after", "before", "upon",
    # Status-field values from promoted frontmatter blocks ("Status: Alive").
    "alive", "deceased", "missing", "unknown", "active", "retired", "dead",
    "recovering", "bound", "imprisoned", "free", "captured",
}
NAME_WORD = re.compile(r"[A-Z][a-zA-Z'’\-]*[a-z][a-zA-Z'’\-]*|[A-Z]{2,}")
# Phrases never cross a line break: "Status: Alive\nLocation:" is a field
# list, not the name "Alive Location". Single-word titles like "Alive" alone
# are then handled by the noise filters.
PHRASE = re.compile(
    r"\b[A-Z][\w'’\-]*(?:(?:[ \t]+(?:of|the|de|le|la|von|van))+[ \t]+[A-Z][\w'’-]*"
    r"|[ \t]+[A-Z][\w'’-]*){0,3}")


class GapEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_id: UUID
    excerpt: str


class GapAliasCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID
    canonical_name: str
    entity_kind: EntityKind | None = None


class IdentityGap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    surface: str
    normalized_surface: str
    claims_with_phrase: int
    total_mentions: int
    retrieval_demand: int = 0
    role_hint: bool = False
    suggested_canonical_name: str | None = None
    suggested_kind: EntityKind | None = None
    related_surfaces: tuple[str, ...] = ()
    evidence: tuple[GapEvidence, ...] = ()
    alias_candidates: tuple[GapAliasCandidate, ...] = ()


class IdentityGapQueue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    gaps: tuple[IdentityGap, ...]
    total_candidates: int


class AddAliasDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    surface: str = Field(min_length=1)
    entity_id: UUID
    idempotency_key: str = Field(min_length=1)


class CreateEntityDecision(BaseModel):
    """Create an identity, optionally merging related surfaces as its aliases.

    Merging is this explicit command — never an automatic clustering. Each
    alias surface must be evidenced by a current claim and ownable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    surface: str = Field(min_length=1)
    entity_kind: EntityKind
    alias_surfaces: tuple[str, ...] = ()
    manual_aliases: tuple[str, ...] = ()
    idempotency_key: str = Field(min_length=1)


class SurfaceDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    surface: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class CorrectCanonicalNameDecision(BaseModel):
    """Rename an identity's canonical name (audited; the old name survives
    as an alias so existing surface references keep resolving). The third
    blocked case (Ishirala Tower, Mads) made the gap concrete: canonical
    names ARE correctable identity facts, not immutable ones."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID
    new_name: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1)


class MarkMisspellingDecision(BaseModel):
    """Record a surface as a misspelling of an existing identity.

    Resolvable for lookups and claim linking, but presented as a correction —
    never as one of the identity's names.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    surface: str = Field(min_length=1)
    entity_id: UUID
    idempotency_key: str = Field(min_length=1)


class MembershipDecision(BaseModel):
    """Explicit faction membership: a roster record, not an alias.

    add=True records membership (optionally a role title and evidence claim);
    add=False removes the current record through supersession.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    faction_id: UUID
    member_id: UUID
    add: bool = True
    role_title: str | None = None
    source_claim_id: UUID | None = None
    idempotency_key: str = Field(min_length=1)


class RoleDecision(BaseModel):
    """Seat a roster member in a faction role, or clear their seat.

    role_name=None clears the member's role (membership survives). Assigning a
    role the member already holds, or a leadership seat held by another member,
    is refused by name — succession is two explicit decisions. is_leadership is
    honored only when the assignment defines a brand-new role.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    faction_id: UUID
    member_id: UUID
    role_name: str | None = None
    is_leadership: bool = False
    source_claim_id: UUID | None = None
    idempotency_key: str = Field(min_length=1)


class RoleDefinitionDecision(BaseModel):
    """Define a role for a faction without seating anyone (a vacant seat)."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    faction_id: UUID
    role_name: str = Field(min_length=1)
    is_leadership: bool = False
    idempotency_key: str = Field(min_length=1)


class FactionRoleSummary(BaseModel):
    """One role definition in the cross-faction roles listing."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    faction_id: UUID
    faction_name: str
    name: str
    is_leadership: bool = False
    holders: tuple[tuple[UUID, str], ...] = ()


class IdentityDecisionEntry(BaseModel):
    """One recorded decision from the durable audit trail, newest first."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    decision_id: UUID
    kind: str
    surface: str
    decided_at: datetime
    details: dict | None = None


class RoleDeclarationSummary(BaseModel):
    """A role surface declared during Identity Review, not yet linked.

    mark_role decisions record vocabulary ("Inquisitor is a role word"); they
    carry no faction linkage. Linking one to a faction is the explicit
    define-role decision, at which point it leaves this listing.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    surface: str
    normalized_surface: str


class RevertDecision(BaseModel):
    """Reverse one prior decision by its receipt; both stay in audit history."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    decision_id: UUID
    idempotency_key: str = Field(min_length=1)


class IdentityDecisionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    decision_id: UUID
    kind: str
    surface: str
    entity_id: UUID | None
    linked_claims: int = 0
    details: dict | None = None
    idempotent_replay: bool


class IdentityQueueError(ValueError):
    """An identity decision failed a deterministic rule."""


def normalize_surface(value: str) -> str:
    """Casefold, collapse whitespace, strip possessives, and trim connectors.

    Possessive forms ("Romulus's") must resolve to their owner. A capitalized
    article is stripped so sentence-initial mentions aggregate with embedded
    ones. Known limitation: a capitalized non-name word starting a mention
    ("Members of the Court of the Stars") yields a distinct surface — the
    queue surfaces what it finds; merging surfaces stays a human decision.
    """
    stripped = re.sub(r"['’]s$", "", value.strip())
    stripped = re.sub(r"['’]$", "", stripped).strip()
    words = stripped.casefold().split()
    while words and words[0] in CONNECTORS:
        words = words[1:]
    while words and words[-1] in CONNECTORS:
        words = words[:-1]
    return " ".join(words)


def strip_title_prefix(surface: str) -> str | None:
    """Canonical name suggestion with person-title prefixes removed.

    "King Peter le Fleur" → "Peter le Fleur": the title is a role, not the
    name; the full form stays available as an alias.
    """
    words = surface.split()
    index = 0
    while index < len(words) and words[index].casefold() in TITLE_PREFIX_WORDS:
        index += 1
    remainder = " ".join(words[index:])
    return remainder if remainder and remainder != surface else None


def suggest_kind(normalized: str, alias_candidate_kinds: list[str]) -> str | None:
    """Deterministic kind proposal: alias-target affinity first, then tail word.

    A suggestion, never an assignment — the selector stays editable.
    """
    distinct = set(alias_candidate_kinds)
    if len(distinct) == 1:
        return next(iter(distinct))
    content = [word for word in normalized.split() if word not in CONNECTORS]
    for word in reversed(content):
        for kind, tails in KIND_TAIL_WORDS.items():
            if word in tails:
                return kind
    return None


def _content_words(normalized: str) -> set[str]:
    return {word for word in normalized.split() if word not in CONNECTORS}


def related_surfaces(gaps: list[IdentityGap]) -> dict[str, tuple[str, ...]]:
    """Surfaces that look like variants of one identity, presented — never merged.

    Two unresolved surfaces relate when their content-word sets overlap
    substantially (subset either way, or Jaccard at least one half) or when
    they share a distinctive word outside the common organizational nouns.
    Sharing a head noun ("Church of Malygos" / "Cult of Malygos") makes them
    *related*, which is exactly why they are shown side by side: the merge is
    a human ruling, and so is the refusal.
    """
    mapping: dict[str, tuple[str, ...]] = {}
    for gap in gaps:
        words = _content_words(gap.normalized_surface)
        if not words:
            continue
        related = []
        for other in gaps:
            if other.normalized_surface == gap.normalized_surface:
                continue
            other_words = _content_words(other.normalized_surface)
            if not other_words:
                continue
            union = words | other_words
            overlap = len(words & other_words) / len(union)
            distinctive_shared = bool(
                (words & other_words) - COMMON_TAIL_WORDS)
            if (words <= other_words or other_words <= words
                    or overlap >= 0.5 or distinctive_shared):
                related.append(other.surface)
        if related:
            mapping[gap.normalized_surface] = tuple(sorted(related))
    return mapping


def role_hint_surfaces(mark_role_surfaces: list[str]) -> set[str]:
    """Final content words of surfaces the DM marked as roles or titles.

    A new gap ending in one of these words carries a non-blocking hint —
    precedent, not automation.
    """
    finals: set[str] = set()
    for surface in mark_role_surfaces:
        words = [word for word in normalize_surface(surface).split()
                 if word not in CONNECTORS]
        if words:
            finals.add(words[-1])
    return finals


def _suffix_surfaces(match_text: str) -> list[str]:
    """Group-boundary suffixes of a phrase match.

    "Members of the Silver Cloaks" yields the full surface and "Silver
    Cloaks": embedded mentions aggregate with sentence-initial ones. Groups
    are maximal runs of non-connector words; connectors are detected
    case-insensitively, so a capitalized leading article is not a group.
    """
    words = match_text.split()
    starts = [index for index, word in enumerate(words)
              if word.casefold() not in CONNECTORS
              and (index == 0 or words[index - 1].casefold() in CONNECTORS)]
    return [" ".join(words[start:]) for start in starts] or [match_text]


def mine_gaps(claims, known, *, evidence_limit: int = 3) -> list[IdentityGap]:
    """Mine recurring proper-noun phrases that match no known identity.

    claims: iterable of (claim_id, assertion_text) for current claims.
    known: casefolded canonical names and aliases that already resolve.
    Connector chains ("Court of the Stars") stay whole; words frequent in
    lowercase are sentence-start noise, not names. Surfaces recurring in at
    least two claims qualify; display keeps the first-seen original casing.
    """
    known = {normalize_surface(name) for name in known}
    lowercase_common: Counter[str] = Counter()
    for _, text in claims:
        lowercase_common.update(
            word for word in re.findall(r"[a-z][\w'’\-]+", text)
            if word not in CONNECTORS)

    claim_counts: Counter[str] = Counter()
    mention_counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    evidence: dict[str, list[tuple[str, str]]] = {}

    for claim_id, text in claims:
        seen: set[str] = set()
        for match in PHRASE.finditer(text):
            for surface in _suffix_surfaces(" ".join(match.group(0).split())):
                key = normalize_surface(surface)
                if key in seen or key in known or key in NON_NAMES:
                    continue
                words = [word for word in surface.split()
                         if word.casefold() not in CONNECTORS]
                if not words or not all(NAME_WORD.fullmatch(word) for word in words):
                    continue
                if words and all(lowercase_common[word.lower()] > 10 for word in words):
                    continue
                seen.add(key)
                mention_counts[key] += 1
                # Display keeps original casing but drops the possessive, so a
                # key aggregated from "Inquisition's" is titled "Inquisition".
                display.setdefault(key, re.sub(r"['’]s?$", "", surface))
                if len(evidence.setdefault(key, [])) < evidence_limit:
                    start = max(0, match.start() - 60)
                    end = min(len(text), match.end() + 60)
                    evidence[key].append((str(claim_id),
                                          text[start:end].replace("\n", " ").strip()))
        claim_counts.update(seen)

    gaps = []
    for key, claims_with in claim_counts.most_common():
        if claims_with < 2:
            continue
        gaps.append(IdentityGap(
            surface=display[key], normalized_surface=key,
            claims_with_phrase=claims_with, total_mentions=mention_counts[key],
            evidence=tuple(GapEvidence(claim_id=UUID(claim_id), excerpt=excerpt)
                           for claim_id, excerpt in evidence[key])))
    return gaps
