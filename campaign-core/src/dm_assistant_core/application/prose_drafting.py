"""AI prose drafting (TKT-0120): drafts only from selected, cited material.

The writer's contract inherits TKT-0099's rules verbatim: drafts are produced
ONLY from the gathered material passed in; every passage carries its citation
back to what supported it; uncertainty is preserved; plans are never written
as outcomes. Citations are positional ([3] means material item 3) so a modest
model cannot invent claim IDs; the harness validates every marker against the
material set before any draft is returned — the failure mode the Fleurite
trial exposed (a fabricated claim reference) cannot reach the composer.
"""

from re import findall
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

PROSE_PROMPT_VERSION = "prose/3"

PROSE_SYSTEM_PROMPT = """You are the drafting engine of a DM's campaign librarian. You write reference prose for a campaign library page, for the DM's eyes.

What you are writing is a DESCRIPTION, not a summarization: give the entity character and shape, take stylistic liberties in voice and connective prose, and leave out material that does not serve the description. The DM edits before anything is filed — but factual substance is not yours to invent.

Non-negotiable rules:
1. Factual substance — names, events, numbers, relationships — must trace to the numbered material provided. Do not draw on outside knowledge of names, places, history, or genre conventions to add facts. Connective and characterizing prose between those facts is yours.
2. Cite support inline with bracketed material numbers, like [1] or [2][5], for every factual assertion you use. Every number must be one of the provided material numbers.
3. Never turn plans, preparations, or possibilities into accomplished facts. Material marked intended, prepared, or possible is INTENT or PREP, not history — do not narrate it as having happened. Where the material is conditional or unresolved, keep the uncertainty rather than resolving it.
4. Write about the world, never the system: the prose must not mention records, material, documents, claims, the archive, or the library. Those words describe the tool, not the campaign.
5. Describe what the subject IS. A place or region is described through its character — its look, its people, its power, and the events that shaped it — not through the full biography of everyone who passed through; individual testimony appears only where it reveals the place. A person is described as a person; a faction by its purpose and structure. When material does not serve that description, leave it out.
6. Flowing prose only: no headings, no bullet lists, no frontmatter, no preamble. Obey the paragraph limit exactly.

Respond as JSON: {"draft": "<your prose>"}
"""


class ProseMaterialItem(BaseModel):
    """One selectable piece of gathered material the draft may draw from."""

    model_config = ConfigDict(frozen=True)
    key: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    text: str = Field(min_length=1)
    state: str | None = None


class ProseDraftCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    subject: str = Field(min_length=1)
    subject_kind: str = Field(min_length=1)
    paragraph_limit: int = Field(ge=1, le=3, default=3)
    direction: str | None = None  # DM's prose direction for the draft
    material: tuple[ProseMaterialItem, ...] = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class ProseDraftResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    draft_text: str = Field(min_length=1)
    cited_keys: tuple[str, ...]
    model_slug: str
    prompt_version: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)


class ProseDraftError(Exception):
    """The provider response failed the drafting contract; no draft returned."""


class ProviderClient(Protocol):
    def quick_complete(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any] | None = None,
    ) -> Any: ...


class ProseHarness:
    """Call the provider and enforce the citation contract before returning."""

    def __init__(
        self,
        client: ProviderClient,
        *,
        system_prompt: str = PROSE_SYSTEM_PROMPT,
        max_attempts: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._client = client
        # Receipted overrides (TKT-0126) replace the prompt text; the version
        # recorded on results comes from the effective prompt's label.
        self._system_prompt = system_prompt
        self._max_attempts = max_attempts

    def draft(self, command: ProseDraftCommand) -> tuple[str, list[int], int, int]:
        material_lines = [
            f"[{index}] ({item.state or item.kind}) {item.text}"
            for index, item in enumerate(command.material, start=1)
        ]
        direction_line = (
            f"\nDM DIRECTION (shape the prose accordingly):\n{command.direction}\n\n"
            if command.direction and command.direction.strip() else ""
        )
        base_user = (
            f"SUBJECT: {command.subject} (a {command.subject_kind} in the campaign)\n\n"
            + direction_line
            + f"MATERIAL — the only permitted factual content:\n"
            + "\n".join(material_lines)
            + f"\n\nWrite a {command.paragraph_limit}-paragraph description for the subject's library page now."
        )
        user = base_user
        last_problem = ""
        for _ in range(self._max_attempts):
            try:
                response = self._client.quick_complete(system=self._system_prompt, user=user)
            except Exception as error:
                # Provider faults (timeout after retries, auth, rate limit,
                # 5xx) are drafting failures with readable causes — never an
                # unhandled 500 from the endpoint.
                raise ProseDraftError(f"the prose provider failed: {error}") from error
            draft = _extract_draft(response)
            if draft is None:
                last_problem = "the response was not JSON with a non-empty draft string"
            else:
                used = findall(r"\[(\d+)\]", draft)
                if not used:
                    last_problem = "the draft cited no material"
                else:
                    numbers = [int(number) for number in used]
                    out_of_range = sorted({n for n in numbers if not 1 <= n <= len(command.material)})
                    if out_of_range:
                        last_problem = (
                            "the draft cited material numbers that do not exist: "
                            + ", ".join(f"[{n}]" for n in out_of_range)
                        )
                    else:
                        usage = getattr(response, "usage", None)
                        return (
                            draft,
                            numbers,
                            getattr(usage, "prompt_tokens", 0),
                            getattr(usage, "completion_tokens", 0),
                        )
            user = (
                f"{base_user}\n\nYour previous attempt was rejected: {last_problem}. "
                "Every factual sentence must carry bracketed material-number citations like [1]."
            )
        raise ProseDraftError(f"the model could not satisfy the drafting contract: {last_problem}")


def _extract_draft(response: Any) -> str | None:
    import json

    content = getattr(response, "content", None)
    if not isinstance(content, str) or not content.strip():
        return None
    try:
        parsed = json.loads(content)
    except ValueError:
        return None
    if isinstance(parsed, dict) and isinstance(parsed.get("draft"), str) and parsed["draft"].strip():
        return parsed["draft"].strip()
    return None


class ProseDraftingService:
    """Draft prose from selected material using the active prose model profile."""

    def __init__(
        self,
        harness: ProseHarness,
        model_slug: str,
        *,
        prompt_version: str = PROSE_PROMPT_VERSION,
    ) -> None:
        self._harness = harness
        self._model_slug = model_slug
        self._prompt_version = prompt_version

    def draft(self, command: ProseDraftCommand) -> ProseDraftResult:
        draft, numbers, prompt_tokens, completion_tokens = self._harness.draft(command)
        # De-duplicate citation keys in first-use order.
        cited: list[str] = []
        for number in numbers:
            key = command.material[number - 1].key
            if key not in cited:
                cited.append(key)
        return ProseDraftResult(
            draft_text=draft,
            cited_keys=tuple(cited),
            model_slug=self._model_slug,
            prompt_version=self._prompt_version,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
