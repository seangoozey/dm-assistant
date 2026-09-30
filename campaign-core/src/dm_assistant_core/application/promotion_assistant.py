"""AI promotion assistant (TKT-0137): suggestions, never decisions.

ADR-0018 point 7 fixes the AI seams; this service fills two of them for the
Lore surface. The headline is restatement matching (the Osirus lesson — the
DM's real toil was recognizing which statements already exist, and the
deterministic term-overlap mirror missed every paraphrase). Secondary:
statement suggestions and the Link/Consider pre-sort. State and subject
opinions stay out of v1 — the defaults carried every live statement.

The model returns positional references only (statement numbers, material
numbers) so a modest model cannot invent claim IDs; the harness validates
every reference against the provided sets before anything is returned, and
malformed or partial output becomes a readable provider fault. Suggestions
are never auto-included (ADR-0018 point 8): they arrive excluded and
wand-marked with provenance; the DM's include-or-exclude decision stays the
compliance mechanism. Stage 3 (commit) has no AI involvement at all.
"""

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

PROMOTION_PROMPT_VERSION = "promotion/1"

PROMOTION_SYSTEM_PROMPT = """You are the promotion assistant of a DM's campaign librarian. You help review new lore before it becomes canon, for the DM's eyes.

You receive numbered STATEMENTS (sentences from a draft description for a new record) and numbered MATERIAL (gathered evidence claims about the campaign). Respond as JSON with exactly these keys:

1. "restatements": pairs where a statement merely restates a piece of material — the same fact said in different words. Judge MEANING, not word overlap: a true paraphrase shares almost no vocabulary with the material. Format: {"statement": <statement number>, "material": <material number>}. Only a restatement of the same fact qualifies; a related but different fact is not a restatement. Empty list when none.
2. "statements": 3 to 6 additional assertions the new record might establish, drawn ONLY from the numbered material. Each: {"text": "<one assertion>", "state": "established" or "considered" or "prepared", "basis": <material number>}. "established" means the material asserts it as fact; "considered" means the material only suggests it; "prepared" means the material describes an intent, plan, or preparation. Never invent facts, never draw on outside knowledge.
3. "links": pieces of material that are really ABOUT the new record itself — the record is the subject of the assertion, not merely mentioned in passing. Each: {"material": <material number>, "reason": "<one line why>"}. Empty list when the material only mentions the record as context.

Respond as JSON: {"restatements": [], "statements": [], "links": []}
"""

_ALLOWED_SUGGESTED_STATES = {"established", "considered", "prepared"}
_MAX_STATEMENT_SUGGESTIONS = 8


class PromotionSuggestionMaterial(BaseModel):
    """One gathered piece of evidence, addressed by position in the prompt."""

    model_config = ConfigDict(frozen=True)
    key: str = Field(min_length=1)
    text: str = Field(min_length=1)
    state: str | None = None


class PromotionSuggestionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    surface: str  # "lore" and "description" ship; others are refused
    subject: str = Field(min_length=1)
    subject_kind: str = Field(min_length=1)
    prose: str = ""  # the draft description; empty skips the restatement pass
    # Explicit statements (the Description surface's :: rows, as the DM edited
    # them) override the prose split; Lore keeps deriving from the prose.
    statements: tuple[str, ...] = ()
    material: tuple[PromotionSuggestionMaterial, ...] = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class RestatementSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)
    statement_number: int = Field(ge=1)
    statement_text: str = Field(min_length=1)
    material_key: str = Field(min_length=1)


class StatementSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str = Field(min_length=1)
    state: str
    basis_key: str = Field(min_length=1)


class LinkSuggestion(BaseModel):
    model_config = ConfigDict(frozen=True)
    material_key: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class PromotionSuggestionSet(BaseModel):
    model_config = ConfigDict(frozen=True)
    surface: str
    subject: str
    restatements: tuple[RestatementSuggestion, ...]
    # The DETERMINISTIC mirror result over the same statements — computed by
    # restates_claim (term overlap), never by the model, so the review's
    # agreement coloring has a system value to join against (green = both,
    # blue = system only, orange = AI only).
    system_restatements: tuple[RestatementSuggestion, ...] = ()
    statements: tuple[StatementSuggestion, ...]
    links: tuple[LinkSuggestion, ...]
    model_slug: str
    prompt_version: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)


class PromotionSuggestionError(Exception):
    """The provider response failed the suggestion contract; nothing returned."""


class ProviderClient(Protocol):
    def quick_complete(
        self, *, system: str, user: str, response_schema: dict[str, Any] | None = None
    ) -> Any: ...


class PromotionSuggestionHarness:
    """Call the provider and enforce the positional-reference contract."""

    def __init__(
        self,
        client: ProviderClient,
        *,
        system_prompt: str = PROMOTION_SYSTEM_PROMPT,
        max_attempts: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._client = client
        # Receipted overrides (TKT-0126) replace the prompt text; the version
        # recorded on results comes from the effective prompt's label.
        self._system_prompt = system_prompt
        self._max_attempts = max_attempts

    def suggest(
        self, command: PromotionSuggestionCommand
    ) -> tuple[
        list[tuple[int, int]],  # (statement_number, material_number)
        list[tuple[str, str, int]],  # (text, state, basis material_number)
        list[tuple[int, str]],  # (material_number, reason)
        int,
        int,
    ]:
        # The Description surface sends its reviewed :: rows verbatim (the DM
        # may have edited them after the split); Lore derives from the prose.
        statements = (
            [text.strip() for text in command.statements if text.strip()]
            if command.statements else _split_statements(command.prose)
        )
        statement_lines = [
            f"{index}. {text}" for index, text in enumerate(statements, start=1)
        ] or ["none — the draft description is empty"]
        material_lines = [
            f"[{index}] ({item.state or 'material'}) {item.text}"
            for index, item in enumerate(command.material, start=1)
        ]
        base_user = (
            f"SUBJECT: {command.subject} (a new {command.subject_kind} record)\n\n"
            f"STATEMENTS — sentences from the draft description:\n"
            + "\n".join(statement_lines)
            + "\n\nMATERIAL — the gathered evidence:\n"
            + "\n".join(material_lines)
            + "\n\nSuggest restatements, statements, and links now."
        )
        user = base_user
        last_problem = ""
        for _ in range(self._max_attempts):
            try:
                response = self._client.quick_complete(system=self._system_prompt, user=user)
            except Exception as error:
                raise PromotionSuggestionError(
                    f"the promotion assistant provider failed: {error}"
                ) from error
            parsed = _extract_payload(response)
            if parsed is None:
                last_problem = "the response was not JSON with the three suggestion lists"
            else:
                try:
                    return (
                        _validated_restatements(parsed.get("restatements"), statements, len(command.material)),
                        _validated_statements(parsed.get("statements"), len(command.material)),
                        _validated_links(parsed.get("links"), len(command.material)),
                        getattr(getattr(response, "usage", None), "prompt_tokens", 0),
                        getattr(getattr(response, "usage", None), "completion_tokens", 0),
                    )
                except ValueError as error:
                    last_problem = str(error)
            user = (
                f"{base_user}\n\nYour previous attempt was rejected: {last_problem}. "
                "Every number must address the provided STATEMENTS or MATERIAL lists."
            )
        raise PromotionSuggestionError(
            f"the model could not satisfy the suggestion contract: {last_problem}"
        )


def _split_statements(prose: str) -> list[str]:
    if not prose.strip():
        return []
    from dm_assistant_core.application.promotion import split_statements

    return [text for _start, _end, text in split_statements(prose)]


def _extract_payload(response: Any) -> dict[str, Any] | None:
    import json

    content = getattr(response, "content", None)
    if not isinstance(content, str) or not content.strip():
        return None
    try:
        parsed = json.loads(content)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _validated_restatements(
    payload: Any, statements: list[str], material_count: int
) -> list[tuple[int, int]]:
    if payload is None:
        raise ValueError("the response was missing restatements")
    if not isinstance(payload, list):
        raise ValueError("restatements must be a list")
    pairs: list[tuple[int, int]] = []
    seen: set[int] = set()
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("each restatement must be an object")
        statement_number = _as_int(entry.get("statement"))
        material_number = _as_int(entry.get("material"))
        if statement_number is None or not 1 <= statement_number <= len(statements):
            raise ValueError("a restatement named a statement number that does not exist")
        if material_number is None or not 1 <= material_number <= material_count:
            raise ValueError("a restatement named a material number that does not exist")
        if statement_number in seen:
            continue  # one restatement per statement; first wins
        seen.add(statement_number)
        pairs.append((statement_number, material_number))
    return pairs


def _validated_statements(payload: Any, material_count: int) -> list[tuple[str, str, int]]:
    if payload is None:
        raise ValueError("the response was missing statements")
    if not isinstance(payload, list):
        raise ValueError("statements must be a list")
    results: list[tuple[str, str, int]] = []
    for entry in payload[:_MAX_STATEMENT_SUGGESTIONS]:
        if not isinstance(entry, dict):
            raise ValueError("each statement suggestion must be an object")
        text = entry.get("text")
        state = entry.get("state")
        basis = _as_int(entry.get("basis"))
        if not isinstance(text, str) or not text.strip():
            raise ValueError("a statement suggestion had no text")
        if state not in _ALLOWED_SUGGESTED_STATES:
            raise ValueError(
                "a statement suggestion named a state outside established/considered/prepared"
            )
        if basis is None or not 1 <= basis <= material_count:
            raise ValueError("a statement suggestion cited a basis material number that does not exist")
        results.append((text.strip(), state, basis))
    return results


def _validated_links(payload: Any, material_count: int) -> list[tuple[int, str]]:
    if payload is None:
        raise ValueError("the response was missing links")
    if not isinstance(payload, list):
        raise ValueError("links must be a list")
    results: list[tuple[int, str]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("each link suggestion must be an object")
        material_number = _as_int(entry.get("material"))
        reason = entry.get("reason")
        if material_number is None or not 1 <= material_number <= material_count:
            raise ValueError("a link suggestion named a material number that does not exist")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("a link suggestion had no reason")
        results.append((material_number, reason.strip()))
    return results


class PromotionAssistantService:
    """Suggest restatements, statements, and links for a promotion review."""

    def __init__(
        self,
        harness: PromotionSuggestionHarness,
        model_slug: str,
        *,
        prompt_version: str = PROMOTION_PROMPT_VERSION,
    ) -> None:
        self._harness = harness
        self._model_slug = model_slug
        self._prompt_version = prompt_version

    def suggest(self, command: PromotionSuggestionCommand) -> PromotionSuggestionSet:
        if command.surface not in ("lore", "description"):
            raise PromotionSuggestionError(
                "the promotion assistant ships on the Lore and Description surfaces"
            )
        pairs, statement_suggestions, links, prompt_tokens, completion_tokens = (
            self._harness.suggest(command)
        )
        statements = (
            [text.strip() for text in command.statements if text.strip()]
            if command.statements else _split_statements(command.prose)
        )
        restatements = tuple(
            RestatementSuggestion(
                statement_number=statement_number,
                statement_text=statements[statement_number - 1],
                material_key=command.material[material_number - 1].key,
            )
            for statement_number, material_number in pairs
        )
        suggestion_statements = tuple(
            StatementSuggestion(
                text=text, state=state, basis_key=command.material[basis - 1].key
            )
            for text, state, basis in statement_suggestions
        )
        return PromotionSuggestionSet(
            surface=command.surface,
            subject=command.subject,
            restatements=restatements,
            system_restatements=_system_mirror(statements, command.material),
            statements=suggestion_statements,
            links=tuple(
                LinkSuggestion(
                    material_key=command.material[material_number - 1].key, reason=reason
                )
                for material_number, reason in links
            ),
            model_slug=self._model_slug,
            prompt_version=self._prompt_version,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


def _system_mirror(
    statements: list[str], material: tuple[PromotionSuggestionMaterial, ...]
) -> tuple[RestatementSuggestion, ...]:
    """The deterministic term-overlap mirror over the same statement set.

    Runs against the material whose keys parse as claim UUIDs (graph-wrapped
    Lore keys skip — Lore carries its system value from derive instead). This
    is the system's own opinion, never the model's: the review joins the two
    into the agreement coloring.
    """
    from uuid import UUID

    from dm_assistant_core.application.promotion import ClaimSummary, restates_claim

    claims = []
    for item in material:
        try:
            claims.append(ClaimSummary(claim_id=UUID(item.key), assertion_text=item.text))
        except ValueError:
            continue
    if not claims:
        return ()
    mirror: list[RestatementSuggestion] = []
    for number, text in enumerate(statements, start=1):
        matched = restates_claim(text, tuple(claims))
        if matched is not None:
            mirror.append(
                RestatementSuggestion(
                    statement_number=number,
                    statement_text=text,
                    material_key=str(matched.claim_id),
                )
            )
    return tuple(mirror)
