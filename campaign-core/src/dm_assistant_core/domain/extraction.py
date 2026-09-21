# Prompt lines stay intact because their boundaries are part of the provider instruction.
# ruff: noqa: E501

"""Bounded AI extraction harness with typed contracts and grounding (TKT-0034).

The harness sits between the OpenRouter provider (TKT-0033) and the candidate pipeline
(TKT-0035). It takes source text, asks the provider to extract structured assertions
against a typed schema contract, validates the response, and enforces a grounding check:
every extracted assertion must be supported by text that appears in the submitted source.
Ungrounded or malformed output is rejected — it never becomes a stored candidate.

Extraction output is always non-canonical. The harness has no path to entities, claims,
or relationships. Promotion remains the existing human-controlled proposal path.
"""

from __future__ import annotations

import json
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from dm_assistant_core.domain.models import ClaimState, Visibility


class ExtractionAuthority(StrEnum):
    """The authority values an extraction may propose.

    These mirror the importer's ``CandidateAuthority`` string values so a candidate
    pipeline (TKT-0035) can map directly. The enum lives here to avoid a circular
    import between the domain and importer packages.
    """

    REAL_PLAY = "real_play"
    EXPLICIT_LORE = "explicit_lore"
    NPC_INTENTION = "npc_intention"
    PREPARATION = "preparation"
    BRAINSTORM = "brainstorm"
    UNCLASSIFIED = "unclassified"


class SubjectResolution(StrEnum):
    """Core-derived status of the principal subject mention."""

    FOCAL_ENTITY = "focal_entity"
    NAMED_IDENTITY = "named_identity"
    NON_ENTITY = "non_entity"
    UNRESOLVED = "unresolved"


#: Minimum character overlap for an extracted quote to be considered grounded.
#: The check is deliberately conservative: the quoted excerpt must appear in the source
#: text (after whitespace normalization) so a confabulated assertion is caught.
_GROUNDING_MIN_EXCERPT_LEN = 5

#: The system prompt instructing the model to extract structured, grounded assertions.
_LEGACY_EXTRACTION_SYSTEM_PROMPT = """\
You are a campaign records clerk for a D&D campaign. You extract factual assertions from \
source text into structured records.

You will receive a source text section to extract from, preceded by document context \
(the file's path, heading, and frontmatter metadata). Use the document context to \
identify the subject entity by name and understand the record type, but ONLY extract \
assertions that are directly supported by the section text itself.

Record-type guidance:
- type: npc → the subject is a DM-controlled character. Use the character's name as the subject.
- type: pc → the subject is a player character. Use the character's name as the subject. \
Do not extract curated profile fields (player, race, sex, status, aliases, or former names) as claims. \
Those fields are canonical PC identity data maintained by the character profile, not campaign assertions.
- type: location → the subject is a place. Use the location name as the subject.
- type: lore → the subject is the lore topic. Use the document heading or topic name.
- type: session-note → events that happened during play are observed/real_play.

For entity-centered documents (pc, npc, and location), the document subject is the focal
entity, but it is not the mandatory subject of every claim. Preserve the grammatical subject
when a clause establishes an independent event or state about a named participant. For
example, "Ruh trained Asha" may become subject "Asha", predicate "was trained by", object
"Ruh" because that inverse is exactly equivalent; "Ruh died during the mission" must remain
subject "Ruh", predicate "died during", object "the mission". Never rewrite the latter as
"Asha witnessed Ruh's death" because witnessing was not stated.

Produce a lossless set of atomic, independently retrievable claims. Every meaningful
numbered source segment must be accounted for. Preserve ages, durations, chronology,
locations, motivations, affiliations, deaths, relationships, and name changes. Split
compound events into separate claims; do not consolidate for brevity. The focal entity is
the default subject, not a mandatory subject when a segment establishes an independent
fact about someone else. Keep predicates short and express one relationship or fact per
assertion. Use object only
for a stable named entity or a meaningful literal value; do not promote generic phrases
such as "missions" or "his parents" into entities. Preserve narrative nuance in
assertion_text rather than packing several events into the predicate.

Semantic fidelity rules:
- Extract only what the text entails. Do not add a plausible consequence, perception,
  cause, intention, survival outcome, or certainty that is not stated.
- "His parents bought him time to escape" does not establish that they died or that he was
  orphaned. "Ruh died during the mission" does not establish that the focal character
  witnessed the death.
- Preserve every stated qualifier that changes retrieval meaning: ages, durations,
  destinations, named route markers, affiliations, titles, leaders, locations, motivations,
  temporal order, and reasons for names or departures.
- If object is non-null, predicate must be the relation only and must not repeat the object.
  Use predicate "was trained by" with object "Ruh", not predicate "was trained by Ruh".
- Use assertion_text to preserve secondary participants or locations that do not fit the
  primary subject-predicate-object relation. Do not silently discard them.
- Before returning, compare each assertion to its cited source segments and remove any word
  that asserts an unstated event or relationship.

Return a JSON object with "assertions" and "coverage" arrays. Each assertion must include:
- subject: the entity name the assertion is about \
(use the proper name from context, not "the character")
- predicate: a short predicate phrase \
(e.g., "is the Herald of", "was born in", "traveled to")
- object: the entity or value the assertion relates to (null if none)
- assertion_text: a faithful summary of the assertion in one sentence
- supporting_excerpt: the exact text from the section that supports this assertion \
(verbatim, not from context)
- state: one of observed, established, intended, prepared, possible
- authority: one of real_play, explicit_lore, npc_intention, preparation, brainstorm
- visibility: one of dm_only, party, character
- confidence: a number between 0 and 1
- source_segment_ids: every numbered source segment supporting this claim

The coverage array must contain exactly one entry for every numbered source segment:
- segment_id: the supplied segment ID
- disposition: extracted, context_only, duplicate, or non_assertive
- claim_indexes: zero-based assertion indexes covering the segment (required for extracted
  and duplicate; empty for context_only and non_assertive)

Use context_only only when text adds context but cannot form an independent assertion.
Use duplicate only when the identified claims already preserve the same fact. Before
returning, perform a coverage pass and add claims for omitted facts. Prefer an additional
grounded claim that a reviewer can deselect over silently dropping a fact.

Authority guidance:
- real_play: something that happened during a play session
- explicit_lore: background facts, established setting detail, administrative metadata
- npc_intention: what an NPC or faction currently plans or wants
- preparation: DM-prepared scenarios or encounters
- brainstorm: speculative or tentative ideas

Visibility guidance:
- dm_only: secrets, GM notes, anything players shouldn't know
- party: things the party knows or has witnessed
- character: specific to one character's knowledge

Only extract assertions directly supported by the section text. Do not invent, infer, or \
hallucinate. The supporting_excerpt must be copied verbatim from the section text (not from \
the document context). If no clear assertions exist, return an empty array."""

EXTRACTION_SYSTEM_PROMPT = """\
You identify atomic factual statements in D&D campaign source text.

Return a JSON object containing only an "assertions" array. For every independent fact,
return:
- assertion_text: a faithful, lossless statement of exactly what the source establishes
- source_segment_ids: every numbered source segment that supports the statement
- subject: the grammatical or stable named subject; use the proper name from context
- predicate: one short relation that does not repeat the object
- object: a named entity or meaningful literal value, otherwise null

Preserve every qualifier that changes retrieval meaning, including ages, durations,
destinations, route markers, affiliations, leaders, locations, motivations, chronology,
titles, and reasons for names or departures. Split compound events into atomic facts.
Do not infer deaths, witnessed events, intentions, causes, or outcomes that are not stated.
A focal document entity is context, not the mandatory subject of every fact.

Campaign Core—not you—will copy exact evidence, assign truth dimensions, and derive segment
coverage. Do not return excerpts, state, authority, visibility, confidence, coverage, or
claim indexes. If no factual statements exist, return an empty assertions array."""


class DocumentContext(BaseModel):
    """Document-level context provided to the extraction model alongside section text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_path: str = Field(min_length=1)
    heading: str | None = None
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    focal_subject: str | None = None
    record_type: str | None = None
    candidate_state: ClaimState | None = None
    candidate_authority: ExtractionAuthority | None = None
    candidate_visibility: Visibility | None = None


class ExtractionError(ValueError):
    """An extraction request failed validation, grounding, or contract checks."""

    failures: tuple[ExtractionAttemptFailure, ...] = ()
    raw_response: str | None = None


class ExtractionAttemptFailure(BaseModel):
    """Derived diagnostic material from one rejected provider attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_number: int = Field(ge=1)
    error: str = Field(min_length=1)
    raw_response: str | None = None


class GroundingError(ExtractionError):
    """An extracted assertion is not grounded in the submitted source text."""


class ExtractedAssertion(BaseModel):
    """One AI-extracted assertion with its claim dimensions and supporting excerpt.

    The ``supporting_excerpt`` must appear verbatim in the source text; the grounding
    check enforces this before the assertion is accepted.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: str = Field(min_length=1, max_length=200)
    subject_resolution: SubjectResolution = SubjectResolution.NAMED_IDENTITY
    predicate: str | None = Field(default=None, min_length=1, max_length=200)
    object: str | None = Field(max_length=200)
    assertion_text: str = Field(min_length=1, max_length=2000)
    supporting_excerpt: str = Field(min_length=1, max_length=2000)
    state: ClaimState
    authority: ExtractionAuthority
    visibility: Visibility
    confidence: Decimal = Field(ge=0, le=1)
    source_segment_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def restrict_extraction_states(self) -> ExtractedAssertion:
        # Extraction proposes observed/established/intended/prepared/possible only.
        # The workflow states (proposed/disputed/superseded/rejected) are system-managed.
        allowed = {
            ClaimState.OBSERVED,
            ClaimState.ESTABLISHED,
            ClaimState.INTENDED,
            ClaimState.PREPARED,
            ClaimState.POSSIBLE,
        }
        if self.state not in allowed:
            raise ValueError(f"extraction cannot propose state {self.state.value}")
        return self


class DiscoveredFact(BaseModel):
    """Minimal provider output; evidence and truth dimensions are Core-owned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: str = Field(min_length=1, max_length=200)
    predicate: str | None = Field(default=None, min_length=1, max_length=200)
    object: str | None = Field(max_length=200)
    assertion_text: str = Field(min_length=1, max_length=2000)
    source_segment_ids: tuple[str, ...] = Field(min_length=1)


class ExtractionResult(BaseModel):
    """The validated output of an extraction call: zero or more grounded assertions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    assertions: tuple[ExtractedAssertion, ...]
    segments: tuple[SourceSegment, ...]
    coverage: tuple[SegmentCoverage, ...]
    extractor_version: str = Field(min_length=1)

    @property
    def is_empty(self) -> bool:
        return len(self.assertions) == 0


class ExtractionContract(BaseModel):
    """The raw JSON contract the provider returns, before validation and grounding.

    This is the wire format; ``ExtractionResult`` is the validated domain form.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    assertions: tuple[DiscoveredFact, ...]


class SourceSegment(BaseModel):
    """One deterministic source clause supplied to and accounted for by the model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_id: str = Field(pattern=r"^s[1-9][0-9]*$")
    text: str = Field(min_length=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)


class SegmentCoverage(BaseModel):
    """The provider's explicit disposition for one deterministic source segment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_id: str = Field(pattern=r"^s[1-9][0-9]*$")
    disposition: Literal["extracted", "context_only", "duplicate", "non_assertive"]
    claim_indexes: tuple[int, ...]


class ProviderClient(Protocol):
    """The provider seam so the harness is testable with a fixture client."""

    def quick_complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> Any: ...


class ExtractionHarness:
    """Call the provider, validate the response, and enforce grounding.

    The harness is the only thing between raw model output and the candidate pipeline.
    It enforces three gates: (1) the response parses as the typed contract, (2) each
    assertion validates against the domain enums and bounds, and (3) each assertion's
    supporting excerpt appears verbatim in the source text. A failure at any gate
    raises and produces no partial output.
    """

    def __init__(
        self,
        client: ProviderClient,
        *,
        extractor_version: str = "extraction/8",
        max_attempts: int = 2,
        system_prompt: str = EXTRACTION_SYSTEM_PROMPT,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._client = client
        self._extractor_version = extractor_version
        self._max_attempts = max_attempts
        # Receipted overrides (TKT-0126) replace the prompt text only; the
        # version recorded with runs comes from the effective prompt label.
        self._system_prompt = system_prompt

    @property
    def extractor_version(self) -> str:
        return self._extractor_version

    def extract(
        self,
        source_text: str,
        *,
        document_context: DocumentContext | None = None,
    ) -> ExtractionResult:
        """Extract grounded assertions from source text.

        When ``document_context`` is provided, the model receives the document's path,
        heading, and frontmatter as framing context so it can identify the subject entity
        and infer the record type. The grounding check still validates excerpts against
        ``source_text`` only — never against the context.

        Raises ``ExtractionError`` if the provider output fails contract validation,
        and ``GroundingError`` if an assertion's supporting excerpt is not found in
        the source text.
        """
        segments = segment_source(source_text)
        user_message = _build_user_message(source_text, document_context, segments)
        last_error: ExtractionError | None = None
        failures: list[ExtractionAttemptFailure] = []
        attempt_message = user_message
        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._extract_once(
                    source_text,
                    document_context=document_context,
                    segments=segments,
                    user_message=attempt_message,
                )
            except ExtractionError as error:
                last_error = error
                failures.append(
                    ExtractionAttemptFailure(
                        attempt_number=attempt,
                        error=str(error),
                        raw_response=getattr(error, "raw_response", None),
                    )
                )
                attempt_message = _build_corrective_retry_message(user_message, str(error))
        assert last_error is not None
        last_error.failures = tuple(failures)
        raise last_error

    def _extract_once(
        self,
        source_text: str,
        *,
        document_context: DocumentContext | None,
        segments: tuple[SourceSegment, ...],
        user_message: str,
    ) -> ExtractionResult:
        normalized_source = _normalize_whitespace(source_text)
        try:
            content = self._client.quick_complete(
                system=self._system_prompt,
                user=user_message,
                response_schema=ExtractionContract.model_json_schema(),
            )
        except Exception as error:
            raise ExtractionError(f"provider request failed: {error}") from error
        raw_text = _extract_content_text(content)
        try:
            contract = self._parse_contract(raw_text)
            assertions, coverage = _materialize_discovered_facts(
                contract,
                segments,
                source_text,
                document_context,
            )
            for assertion in assertions:
                _check_grounding(assertion, normalized_source)
        except ExtractionError as error:
            error.raw_response = raw_text
            raise
        return ExtractionResult(
            assertions=assertions,
            segments=segments,
            coverage=coverage,
            extractor_version=self._extractor_version,
        )

    @staticmethod
    def _parse_contract(raw_text: str) -> ExtractionContract:
        json_text = _extract_json(raw_text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as error:
            raise ExtractionError(f"provider response is not valid JSON: {error.msg}") from error
        if not isinstance(parsed, dict):
            raise ExtractionError("provider response JSON is not an object")
        try:
            return ExtractionContract.model_validate(parsed)
        except ValidationError as error:
            raise ExtractionError(
                f"provider response failed the extraction contract: {error}"
            ) from error


def _build_corrective_retry_message(original: str, validation_error: str) -> str:
    return (
        f"{original}\n\nCORRECTIVE RETRY REQUIRED\n"
        f"The previous response was rejected: {validation_error}\n"
        "Return a complete replacement JSON object. Correct the stated defect, re-check "
        "every exact excerpt and reciprocal segment reference, and do not repeat the "
        "invalid output."
    )


def _extract_content_text(content: Any) -> str:
    """Extract the text content from a provider response object or string."""
    if isinstance(content, str):
        return content
    # ChatCompletionResponse or similar: use the .content property
    text = getattr(content, "content", None)
    if text is None:
        raise ExtractionError("provider response has no content")
    return str(text)


def _build_user_message(
    source_text: str,
    context: DocumentContext | None,
    segments: tuple[SourceSegment, ...],
) -> str:
    """Format the user message with optional document context preceding the source text."""
    import json

    lines: list[str] = []
    if context is not None:
        lines.append("--- Document context ---")
        lines.append(f"Source path: {context.source_path}")
    if context is not None and context.heading:
        lines.append(f"Document heading: {context.heading}")
    if context is not None and context.record_type:
        lines.append(f"Record type: {context.record_type}")
    if context is not None and context.focal_subject:
        lines.append(f"Focal subject: {context.focal_subject}")
    if context is not None and context.candidate_state:
        lines.append(f"Reviewed state: {context.candidate_state.value}")
    if context is not None and context.candidate_authority:
        lines.append(f"Reviewed authority: {context.candidate_authority.value}")
    if context is not None and context.candidate_visibility:
        lines.append(f"Reviewed visibility: {context.candidate_visibility.value}")
    if context is not None and context.frontmatter:
        lines.append(f"Frontmatter: {json.dumps(context.frontmatter, default=str)}")
    if context is not None:
        lines.append("--- End document context ---")
        lines.append("")
    lines.append("--- Section text to extract from ---")
    lines.append(source_text)
    lines.append("--- End section text ---")
    lines.append("")
    lines.append("--- Numbered source segments to account for ---")
    lines.extend(f"[{segment.segment_id}] {segment.text}" for segment in segments)
    lines.append("--- End numbered source segments ---")
    return "\n".join(lines)


def segment_source(source_text: str) -> tuple[SourceSegment, ...]:
    """Split prose deterministically at sentence and explicit clause punctuation."""
    import re

    boundaries = list(
        re.finditer(
            r"(?<=[.!?;])\s+|,\s+(?:and\s+)?|\s+and\s+(?=[A-Z][A-Za-z'-]+\s+[a-z])",
            source_text,
        )
    )
    spans: list[tuple[int, int]] = []
    start = 0
    for boundary in boundaries:
        end = boundary.start()
        if source_text[start:end].strip():
            spans.append((start, end))
        start = boundary.end()
    if source_text[start:].strip():
        spans.append((start, len(source_text)))
    segments: list[SourceSegment] = []
    for index, (raw_start, raw_end) in enumerate(spans, start=1):
        text = source_text[raw_start:raw_end]
        left_trim = len(text) - len(text.lstrip())
        right_trimmed = text.rstrip()
        start_offset = raw_start + left_trim
        end_offset = raw_start + len(right_trimmed)
        segments.append(
            SourceSegment(
                segment_id=f"s{index}",
                text=source_text[start_offset:end_offset],
                start_offset=start_offset,
                end_offset=end_offset,
            )
        )
    return tuple(segments)


def _materialize_discovered_facts(
    contract: ExtractionContract,
    segments: tuple[SourceSegment, ...],
    source_text: str,
    context: DocumentContext | None,
) -> tuple[tuple[ExtractedAssertion, ...], tuple[SegmentCoverage, ...]]:
    """Build grounded domain assertions and reciprocal coverage deterministically."""
    expected = {segment.segment_id for segment in segments}
    assertions: list[ExtractedAssertion] = []
    for index, fact in enumerate(contract.assertions):
        unknown = set(fact.source_segment_ids) - expected
        if unknown:
            raise ExtractionError(f"claim {index} cites an unknown source segment")
        cited = tuple(
            segment for segment in segments if segment.segment_id in fact.source_segment_ids
        )
        exact_excerpt = source_text[
            min(segment.start_offset for segment in cited) : max(
                segment.end_offset for segment in cited
            )
        ]
        subject, subject_resolution = _resolve_source_subject(
            fact.subject, exact_excerpt, source_text, context
        )
        assertions.append(
            ExtractedAssertion(
                subject=subject,
                subject_resolution=subject_resolution,
                predicate=fact.predicate,
                object=fact.object,
                assertion_text=fact.assertion_text,
                supporting_excerpt=exact_excerpt,
                state=context.candidate_state
                if context and context.candidate_state
                else ClaimState.ESTABLISHED,
                authority=context.candidate_authority
                if context and context.candidate_authority
                else ExtractionAuthority.EXPLICIT_LORE,
                visibility=context.candidate_visibility
                if context and context.candidate_visibility
                else Visibility.DM_ONLY,
                confidence=Decimal("1"),
                source_segment_ids=fact.source_segment_ids,
            )
        )
    coverage: list[SegmentCoverage] = []
    for segment in segments:
        indexes = tuple(
            index
            for index, assertion in enumerate(assertions)
            if segment.segment_id in assertion.source_segment_ids
        )
        coverage.append(
            SegmentCoverage(
                segment_id=segment.segment_id,
                disposition="extracted" if indexes else "context_only",
                claim_indexes=indexes,
            )
        )
    return tuple(assertions), tuple(coverage)


def _resolve_source_subject(
    subject: str,
    cited_text: str,
    section_text: str,
    context: DocumentContext | None,
) -> tuple[str, SubjectResolution]:
    """Ground a provider subject in cited text or explicit focal context."""
    import re

    normalized = " ".join(subject.split()).strip()
    context_type = None
    if context:
        context_type = context.record_type or context.frontmatter.get("type")
    focal_value = context.focal_subject if context and context.focal_subject else None
    if (
        not focal_value
        and context
        and context.heading
        and context_type in {"pc", "npc", "location"}
    ):
        focal_value = context.heading
    focal = focal_value.strip() if focal_value else None
    lowered = normalized.casefold()
    focal_pronouns = {"he", "she", "they", "him", "her", "them"}
    non_entity_prefixes = ("his ", "her ", "their ", "the ", "a ", "an ")
    if focal and (lowered == focal.casefold() or lowered in focal_pronouns):
        return focal, SubjectResolution.FOCAL_ENTITY
    possessive = re.match(r"^(.+?)['\u2019]s\s+(.+)$", normalized)
    if lowered.startswith(non_entity_prefixes) or possessive:
        if lowered in section_text.casefold():
            return normalized, SubjectResolution.NON_ENTITY
        return normalized, SubjectResolution.UNRESOLVED
    if lowered in section_text.casefold():
        return normalized, SubjectResolution.NAMED_IDENTITY
    return normalized, SubjectResolution.UNRESOLVED


def _reconcile_segment_references(
    contract: Any,
    segments: tuple[SourceSegment, ...],
    source_text: str,
) -> Any:
    """Resolve evidence to source segments, then copy exact evidence from the source."""
    expected = {segment.segment_id for segment in segments}
    assertions: list[ExtractedAssertion] = []
    for index, assertion in enumerate(contract.assertions):
        excerpt = _normalize_whitespace(assertion.supporting_excerpt)
        matched_ids = tuple(
            segment.segment_id
            for segment in segments
            if excerpt in _normalize_whitespace(segment.text)
            or _normalize_whitespace(segment.text) in excerpt
        )
        unknown = set(assertion.source_segment_ids) - expected
        if unknown:
            raise ExtractionError(f"claim {index} cites an unknown source segment")
        referenced = set(assertion.source_segment_ids)
        referenced.update(
            entry.segment_id
            for entry in contract.coverage
            if index in entry.claim_indexes and entry.segment_id in expected
        )
        segment_ids = matched_ids or tuple(
            segment.segment_id for segment in segments if segment.segment_id in referenced
        )
        if not segment_ids:
            raise GroundingError(
                f"assertion about '{assertion.subject}' has no valid source segment reference"
            )
        cited_segments = tuple(segment for segment in segments if segment.segment_id in segment_ids)
        exact_excerpt = source_text[
            min(segment.start_offset for segment in cited_segments) : max(
                segment.end_offset for segment in cited_segments
            )
        ]
        if not matched_ids and _content_word_overlap(excerpt, exact_excerpt) < 0.3:
            raise GroundingError(
                f"supporting excerpt not found in source text for assertion "
                f"about '{assertion.subject}'"
            )
        assertions.append(
            assertion.model_copy(
                update={
                    "source_segment_ids": segment_ids,
                    "supporting_excerpt": exact_excerpt,
                }
            )
        )

    coverage = tuple(
        entry.model_copy(
            update={
                "claim_indexes": tuple(
                    index
                    for index, assertion in enumerate(assertions)
                    if entry.segment_id in assertion.source_segment_ids
                )
            }
        )
        for entry in contract.coverage
    )
    return contract.model_copy(update={"assertions": tuple(assertions), "coverage": coverage})


def _content_word_overlap(proposed: str, exact: str) -> float:
    import re

    ignored = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "he",
        "her",
        "his",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "she",
        "that",
        "the",
        "their",
        "they",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
    proposed_words = set(re.findall(r"[a-z0-9]+", proposed.lower())) - ignored
    exact_words = set(re.findall(r"[a-z0-9]+", exact.lower())) - ignored
    if not proposed_words or not exact_words:
        return 0.0
    return len(proposed_words & exact_words) / min(len(proposed_words), len(exact_words))


def _align_supporting_excerpts(
    contract: Any,
    segments: tuple[SourceSegment, ...],
) -> Any:
    """Canonicalize a close paraphrase when possible; references provide fallback."""
    import re
    from difflib import SequenceMatcher

    normalized_source = _normalize_whitespace(" ".join(segment.text for segment in segments))
    aligned: list[ExtractedAssertion] = []
    for assertion in contract.assertions:
        excerpt = _normalize_whitespace(assertion.supporting_excerpt)
        if excerpt in normalized_source:
            aligned.append(assertion)
            continue

        excerpt_tokens = re.findall(r"[a-z0-9]+", excerpt.lower())
        best: tuple[float, float, str] | None = None
        for start in range(len(segments)):
            for size in range(1, min(3, len(segments) - start) + 1):
                exact = " ".join(segment.text for segment in segments[start : start + size])
                exact_tokens = re.findall(r"[a-z0-9]+", exact.lower())
                if not excerpt_tokens or not exact_tokens:
                    continue
                shared = len(set(excerpt_tokens) & set(exact_tokens))
                token_recall = shared / len(set(excerpt_tokens))
                sequence = SequenceMatcher(None, excerpt.lower(), exact.lower()).ratio()
                candidate = (token_recall, sequence, exact)
                if best is None or (candidate[0] + candidate[1]) > (best[0] + best[1]):
                    best = candidate
        if best is not None and best[0] >= 0.7 and best[1] >= 0.5:
            aligned.append(assertion.model_copy(update={"supporting_excerpt": best[2]}))
        else:
            aligned.append(assertion)
    return contract.model_copy(update={"assertions": tuple(aligned)})


def _extract_json(text: str) -> str:
    """Extract a JSON object from text that may be wrapped in markdown fences.

    Models frequently wrap structured output in ```` ```json ... `````` or add prose
    around it. This finds the first ``{`` and matching last ``}`` to isolate the JSON
    payload. If the text is already pure JSON, it returns unchanged.
    """
    stripped = text.strip()
    if stripped.startswith("{"):
        return stripped
    # Find the first { and last } — the JSON object boundaries.
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return stripped[first_brace : last_brace + 1]
    return stripped


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _check_grounding(assertion: ExtractedAssertion, normalized_source: str) -> None:
    """Reject an assertion whose supporting excerpt does not appear in the source."""
    if len(assertion.supporting_excerpt) < _GROUNDING_MIN_EXCERPT_LEN:
        raise GroundingError(
            f"supporting excerpt too short for assertion about '{assertion.subject}'"
        )
    normalized_excerpt = _normalize_whitespace(assertion.supporting_excerpt)
    if normalized_excerpt not in normalized_source:
        raise GroundingError(
            f"supporting excerpt not found in source text for assertion about '{assertion.subject}'"
        )


def _normalize_to_context(
    assertion: ExtractedAssertion, context: DocumentContext | None
) -> ExtractedAssertion:
    """Enforce source-owned identity and truth dimensions after provider validation."""
    if context is None:
        return assertion
    updates: dict[str, Any] = {}
    if context.candidate_state is not None:
        updates["state"] = context.candidate_state
    if context.candidate_authority is not None:
        updates["authority"] = context.candidate_authority
    if context.candidate_visibility is not None:
        updates["visibility"] = context.candidate_visibility
    return assertion.model_copy(update=updates) if updates else assertion
