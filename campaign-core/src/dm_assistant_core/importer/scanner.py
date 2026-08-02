"""Deterministic, read-once Markdown discovery and parsing."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from uuid import uuid4

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

from dm_assistant_core.domain import ClaimState, Visibility
from dm_assistant_core.importer.models import (
    CandidateAuthority,
    ImportCandidate,
    ImportClassification,
    ImportOutcome,
    ImportWarning,
    MarkdownScanBatch,
    ScannedSource,
)

INCLUDED_ROOTS = frozenset(
    {"encounters", "gm", "handouts", "locations", "lore", "npcs", "pcs", "sessions", "templates"}
)
WIKI_LINK = re.compile(r"\[\[([^]|#]+)")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)
PLACEHOLDER = "[Not yet established.]"


class SourceSafetyError(ValueError):
    """The configured source tree violates the connector's read-only safety rules."""


class MarkdownScannerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root: Path
    root_identifier: str = Field(min_length=1)
    importer_version: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    path_policy_version: str = Field(min_length=1)
    read_only: Literal[True]
    scan_id: str | None = None
    reextract_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Section:
    title: str
    path: str
    level: int
    content: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class ParsedFrontmatter:
    metadata: dict[str, Any]
    body: str
    body_offset: int
    warning: ImportWarning | None


def _derived_gm_path(relative: PurePosixPath) -> bool:
    return relative == PurePosixPath("gm/location-migration-inventory.md") or (
        len(relative.parts) >= 2 and relative.parts[:2] == ("gm", "location-evidence")
    )


def _parse_frontmatter(text: str) -> ParsedFrontmatter:
    if not text.startswith("---") or (len(text) > 3 and text[3] not in "\r\n"):
        return ParsedFrontmatter({}, text, 0, ImportWarning.MISSING_FRONTMATTER)
    match = re.search(r"\r?\n---[ \t]*(?:\r?\n|$)", text[3:])
    if match is None:
        return ParsedFrontmatter({}, text, 0, ImportWarning.INVALID_FRONTMATTER)
    closing_start = 3 + match.start()
    body_offset = 3 + match.end()
    try:
        loaded = yaml.safe_load(text[3:closing_start])
    except yaml.YAMLError:
        return ParsedFrontmatter(
            {}, text[body_offset:], body_offset, ImportWarning.INVALID_FRONTMATTER
        )
    if not isinstance(loaded, dict):
        return ParsedFrontmatter(
            {}, text[body_offset:], body_offset, ImportWarning.INVALID_FRONTMATTER
        )
    normalized = json.loads(json.dumps(loaded, default=_yaml_scalar))
    return ParsedFrontmatter(normalized, text[body_offset:], body_offset, None)


def _yaml_scalar(value: Any) -> str:
    isoformat = getattr(value, "isoformat", None)
    return str(isoformat()) if callable(isoformat) else str(value)


def _sections(parsed: ParsedFrontmatter) -> tuple[Section, ...]:
    matches = list(HEADING.finditer(parsed.body))
    result: list[Section] = []
    ancestors: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        while ancestors and ancestors[-1][0] >= level:
            ancestors.pop()
        content_start = match.end()
        if content_start < len(parsed.body) and parsed.body[content_start] in "\r\n":
            content_start += 2 if parsed.body[content_start : content_start + 2] == "\r\n" else 1
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(parsed.body)
        content = parsed.body[content_start:content_end].strip()
        if level >= 2:
            section_path = " / ".join(
                [
                    ancestor_title
                    for ancestor_level, ancestor_title in ancestors
                    if ancestor_level >= 2
                ]
                + [title]
            )
            result.append(
                Section(
                    title=title,
                    path=section_path,
                    level=level,
                    content=content,
                    start_offset=parsed.body_offset + content_start,
                    end_offset=parsed.body_offset + content_end,
                )
            )
        ancestors.append((level, title))
    return tuple(result)


def _candidate(
    section: Section,
    *,
    state: ClaimState,
    authority: CandidateAuthority,
    parser_version: str,
    conditional: bool = False,
    evidence_only: bool = False,
) -> ImportCandidate:
    fingerprint_input = "\x1f".join(
        (
            section.path.casefold(),
            " ".join(section.content.split()).casefold(),
            state.value,
            str(section.start_offset),
            str(section.end_offset),
        )
    )
    return ImportCandidate(
        fingerprint=sha256(fingerprint_input.encode()).hexdigest(),
        section=section.path,
        assertion_text=section.content,
        state=state,
        authority=authority,
        visibility=Visibility.DM_ONLY,
        conditional=conditional,
        predicts_pc_action=False,
        evidence_only=evidence_only,
        start_offset=section.start_offset,
        end_offset=section.end_offset,
        extractor_version=parser_version,
    )


def _nonempty_all(sections: tuple[Section, ...], name: str) -> tuple[Section, ...]:
    return tuple(
        section
        for section in sections
        if section.title == name and section.content and PLACEHOLDER not in section.content
    )


def _nonempty(sections: tuple[Section, ...], name: str) -> Section | None:
    matches = _nonempty_all(sections, name)
    return matches[0] if matches else None


def _section_key(section: Section) -> tuple[str, int, int]:
    return (section.path, section.start_offset, section.end_offset)


def _candidate_key(candidate: ImportCandidate) -> tuple[str, int, int]:
    return (candidate.section, candidate.start_offset, candidate.end_offset)


def _planning_dimensions(section: Section) -> tuple[ClaimState, CandidateAuthority]:
    lowered = section.title.casefold()
    if any(marker in lowered for marker in ("prepared", "pressure", "scenario")):
        return (ClaimState.PREPARED, CandidateAuthority.PREPARATION)
    if any(marker in lowered for marker in ("intent", "plan", "goal", "objective")):
        return (ClaimState.INTENDED, CandidateAuthority.NPC_INTENTION)
    return (ClaimState.POSSIBLE, CandidateAuthority.BRAINSTORM)


class MarkdownScanner:
    """Read an admitted source exactly once and produce a transport-safe batch."""

    def __init__(
        self,
        config: MarkdownScannerConfig,
        byte_reader: Callable[[Path], bytes] | None = None,
    ) -> None:
        self.config = config
        self._byte_reader = byte_reader or (lambda path: path.read_bytes())
        self.read_counts: Counter[str] = Counter()

    def scan(self) -> MarkdownScanBatch:
        root = self.config.root.resolve(strict=True)
        if not root.is_dir():
            raise SourceSafetyError("configured Markdown source root is not a directory")
        if self.config.root.is_symlink():
            raise SourceSafetyError("configured Markdown source root cannot be a symbolic link")
        admitted, exclusions = self._discover(root)
        known_targets = {
            PurePosixPath(path).stem.casefold()
            for path, _source in admitted
            if PurePosixPath(path).suffix.casefold() == ".md"
        }
        scanned = tuple(
            self._read_and_parse(root, path, source, known_targets) for path, source in admitted
        )
        snapshot_at = datetime.now(UTC)
        digest_input = "\n".join(
            [
                self.config.scan_id or str(uuid4()),
                self.config.root_identifier,
                self.config.importer_version,
                self.config.parser_version,
                self.config.path_policy_version,
                *(f"reextract\0{path}" for path in self.config.reextract_paths),
                *(f"{source.path}\0{source.content_hash}" for source in scanned),
            ]
        )
        return MarkdownScanBatch(
            root_identifier=self.config.root_identifier,
            snapshot_at=snapshot_at,
            importer_version=self.config.importer_version,
            parser_version=self.config.parser_version,
            path_policy_version=self.config.path_policy_version,
            idempotency_key=f"markdown:{sha256(digest_input.encode()).hexdigest()}",
            reextract_paths=self.config.reextract_paths,
            excluded_paths_encountered=tuple(exclusions),
            files=scanned,
        )

    def _discover(self, root: Path) -> tuple[list[tuple[str, Path]], list[str]]:
        admitted: list[tuple[str, Path]] = []
        excluded: list[str] = []

        def walk(directory: Path, relative_directory: PurePosixPath) -> None:
            for child in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
                relative = relative_directory / child.name
                relative_text = relative.as_posix()
                if child.is_symlink():
                    resolved = child.resolve(strict=True)
                    if not resolved.is_relative_to(root):
                        raise SourceSafetyError(
                            f"symbolic link escapes source root: {relative_text}"
                        )
                    raise SourceSafetyError(f"symbolic links are not admitted: {relative_text}")
                if _derived_gm_path(relative):
                    excluded.append(f"{relative_text}/" if child.is_dir() else relative_text)
                    continue
                resolved = child.resolve(strict=True)
                if not resolved.is_relative_to(root):
                    raise SourceSafetyError(f"discovered path escapes source root: {relative_text}")
                if child.is_dir():
                    walk(child, relative)
                elif child.is_file():
                    admitted.append((relative_text, child))

        for child in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
            relative_text = child.name
            if child.is_symlink():
                resolved = child.resolve(strict=True)
                if not resolved.is_relative_to(root):
                    raise SourceSafetyError(f"symbolic link escapes source root: {relative_text}")
                raise SourceSafetyError(f"symbolic links are not admitted: {relative_text}")
            if not child.is_dir() or child.name not in INCLUDED_ROOTS:
                excluded.append(f"{relative_text}/" if child.is_dir() else relative_text)
                continue
            walk(child, PurePosixPath(child.name))
        admitted.sort(key=lambda item: item[0].casefold())
        return admitted, sorted(excluded, key=str.casefold)

    def _read_and_parse(
        self,
        root: Path,
        relative_path: str,
        source: Path,
        known_targets: set[str],
    ) -> ScannedSource:
        resolved = source.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise SourceSafetyError(f"source escaped configured root before read: {relative_path}")
        self.read_counts[relative_path] += 1
        content = self._byte_reader(source)
        modified_at = datetime.fromtimestamp(source.stat().st_mtime, tz=UTC)
        content_hash = sha256(content).hexdigest()
        if PurePosixPath(relative_path).suffix.casefold() != ".md":
            return ScannedSource(
                path=relative_path,
                content_hash=content_hash,
                content=content,
                filesystem_modified_at=modified_at,
                frontmatter={},
                classification=ImportClassification.QUARANTINE,
                proposed_outcome=ImportOutcome.QUARANTINED,
                candidates=(),
                entity_candidates=0,
                warnings=(ImportWarning.UNKNOWN_FORMAT,),
            )
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return ScannedSource(
                path=relative_path,
                content_hash=content_hash,
                content=content,
                filesystem_modified_at=modified_at,
                frontmatter={},
                classification=ImportClassification.QUARANTINE,
                proposed_outcome=ImportOutcome.QUARANTINED,
                candidates=(),
                entity_candidates=0,
                warnings=(ImportWarning.INVALID_UTF8,),
            )
        return self._classify(
            relative_path, content, content_hash, modified_at, text, known_targets
        )

    def _classify(
        self,
        path: str,
        content: bytes,
        content_hash: str,
        modified_at: datetime,
        text: str,
        known_targets: set[str],
    ) -> ScannedSource:
        relative = PurePosixPath(path)
        parsed = _parse_frontmatter(text)
        metadata = parsed.metadata
        record_type = str(metadata.get("type", ""))
        status = str(metadata.get("status", ""))
        canon_status = str(metadata.get("canon_status", ""))
        review_status = str(metadata.get("review_status", ""))
        delta_status = str(metadata.get("delta_status", ""))
        promotion_status = str(metadata.get("promotion_status", ""))
        sections = _sections(parsed)
        warnings = [parsed.warning] if parsed.warning else []
        candidates: list[ImportCandidate] = []
        entity_candidates = 0

        if relative.parts[0] == "templates":
            classification = ImportClassification.TEMPLATE
            outcome = ImportOutcome.TEMPLATE_EXCLUDED
        elif relative.name == "00_index.md" or record_type.endswith("-index"):
            classification = ImportClassification.NAVIGATION_INDEX
            outcome = ImportOutcome.NAVIGATION_EXCLUDED
        elif _classification_conflicts(relative, record_type, status):
            classification = ImportClassification.QUARANTINE
            outcome = ImportOutcome.QUARANTINED
            warnings.append(ImportWarning.CLASSIFICATION_CONFLICT)
        elif relative.parts[:2] == ("sessions", "notes"):
            classification = ImportClassification.REAL_PLAY_EVIDENCE
            outcome = ImportOutcome.NEW
            if record_type == "session" and status == "note":
                warnings.append(ImportWarning.LEGACY_SESSION_METADATA)
            observed = _nonempty(sections, "Observed Events")
            if observed:
                candidates.append(
                    _candidate(
                        observed,
                        state=ClaimState.OBSERVED,
                        authority=CandidateAuthority.REAL_PLAY,
                        parser_version=self.config.parser_version,
                    )
                )
            if status == "needs-review" and _nonempty(sections, "Canon Deltas"):
                warnings.append(ImportWarning.UNRESOLVED_CANON_DELTAS)
            if status == "applied-delta" and _nonempty(sections, "Canon Deltas"):
                warnings.append(ImportWarning.APPLIED_DELTA_NO_REAPPLY)
            if review_status == "needs-review" and _nonempty(sections, "Canon Deltas"):
                warnings.append(ImportWarning.UNRESOLVED_CANON_DELTAS)
            if delta_status == "applied" and _nonempty(sections, "Canon Deltas"):
                warnings.append(ImportWarning.APPLIED_DELTA_NO_REAPPLY)
            if not candidates:
                original_notes = _nonempty(sections, "Original Notes")
                if original_notes:
                    candidates.append(
                        _candidate(
                            original_notes,
                            state=ClaimState.OBSERVED,
                            authority=CandidateAuthority.REAL_PLAY,
                            parser_version=self.config.parser_version,
                        )
                    )
        elif record_type == "session" and status == "note":
            classification = ImportClassification.QUARANTINE
            outcome = ImportOutcome.QUARANTINED
            warnings.append(ImportWarning.LEGACY_SESSION_WRONG_PATH)
        elif path == "gm/campaign-bible.md":
            classification = ImportClassification.PLANNING_EVIDENCE
            outcome = ImportOutcome.REVIEW_REQUIRED
            for section in sections:
                if (
                    section.content
                    and not _evidence_heading(section.title)
                    and section.title.casefold() != "overview"
                ):
                    state, authority = _planning_dimensions(section)
                    candidates.append(
                        _candidate(
                            section,
                            state=state,
                            authority=authority,
                            parser_version=self.config.parser_version,
                        )
                    )
        elif relative.parts[:2] == ("gm", "brainstorming") or record_type == "brainstorm":
            classification = ImportClassification.NONCANON_EVIDENCE
            outcome = ImportOutcome.NEW
            if _nonempty(sections, "Promotion Receipt"):
                warnings.append(ImportWarning.PROMOTION_RECEIPT_NO_REAPPLY)
            if promotion_status in {"promoted", "partially-promoted"} and (
                ImportWarning.PROMOTION_RECEIPT_NO_REAPPLY not in warnings
            ):
                warnings.append(ImportWarning.PROMOTION_RECEIPT_NO_REAPPLY)
        elif relative.parts[:2] == ("sessions", "prep") or record_type == "session-prep":
            classification = ImportClassification.PLANNED_PREPARATION
            outcome = ImportOutcome.NEW
            recap = _nonempty(sections, "Recap")
            if recap:
                candidates.append(
                    _candidate(
                        recap,
                        state=ClaimState.OBSERVED,
                        authority=CandidateAuthority.REAL_PLAY,
                        parser_version=self.config.parser_version,
                        evidence_only=True,
                    )
                )
            expected = _nonempty(sections, "Expected Outcomes")
            if expected:
                candidates.append(
                    _candidate(
                        expected,
                        state=ClaimState.PREPARED,
                        authority=CandidateAuthority.PREPARATION,
                        parser_version=self.config.parser_version,
                    )
                )
            if not candidates:
                for section in sections:
                    if section.content and not _evidence_heading(section.title):
                        candidates.append(
                            _candidate(
                                section,
                                state=ClaimState.PREPARED,
                                authority=CandidateAuthority.PREPARATION,
                                parser_version=self.config.parser_version,
                            )
                        )
        elif relative.parts[0] == "encounters" or record_type == "encounter":
            classification = ImportClassification.PREPARATION
            outcome = ImportOutcome.NEW
            scenario = _nonempty(sections, "Prepared Scenario")
            if scenario:
                candidates.append(
                    _candidate(
                        scenario,
                        state=ClaimState.PREPARED,
                        authority=CandidateAuthority.PREPARATION,
                        parser_version=self.config.parser_version,
                    )
                    )
            if not candidates:
                for section in sections:
                    if section.content and not _read_aloud_heading(section.title):
                        candidates.append(
                            _candidate(
                                section,
                                state=ClaimState.PREPARED,
                                authority=CandidateAuthority.PREPARATION,
                                parser_version=self.config.parser_version,
                            )
                        )
            if any(
                section.content and _read_aloud_heading(section.title)
                for section in sections
            ):
                warnings.append(ImportWarning.READ_ALOUD_IS_DERIVED)
        elif relative.parts[0] == "handouts":
            classification = ImportClassification.CANONICAL_ARTIFACT
            outcome = ImportOutcome.REVIEW_REQUIRED
        elif (
            relative.parts[0] in {"npcs", "pcs", "locations", "lore"}
            and (status == "canon" or canon_status == "canon")
            and record_type in {"npc", "pc", "location", "lore"}
        ):
            classification = ImportClassification.DURABLE_EVIDENCE
            outcome = ImportOutcome.NEW
            entity_candidates = 1
            for name, state, authority, conditional in (
                (
                    "Established Facts",
                    ClaimState.ESTABLISHED,
                    CandidateAuthority.EXPLICIT_LORE,
                    False,
                ),
                ("Current Goals", ClaimState.INTENDED, CandidateAuthority.NPC_INTENTION, False),
                ("Possibilities", ClaimState.POSSIBLE, CandidateAuthority.BRAINSTORM, False),
                ("Private GM Notes", ClaimState.PREPARED, CandidateAuthority.PREPARATION, True),
            ):
                named_section = _nonempty(sections, name)
                if named_section:
                    candidates.append(
                        _candidate(
                            named_section,
                            state=state,
                            authority=authority,
                            parser_version=self.config.parser_version,
                            conditional=conditional,
                        )
                    )
            used_sections = {_candidate_key(candidate) for candidate in candidates}
            for section in sections:
                if (
                    not section.content
                    or PLACEHOLDER in section.content
                    or _section_key(section) in used_sections
                    or _evidence_heading(section.title)
                ):
                    continue
                lowered = section.title.casefold()
                if "private gm" in lowered:
                    state = ClaimState.PREPARED
                    authority = CandidateAuthority.PREPARATION
                    conditional = relative.parts[0] == "pcs"
                elif "goal" in lowered or "motivation" in lowered:
                    state = (
                        ClaimState.PREPARED
                        if relative.parts[0] == "pcs"
                        else ClaimState.INTENDED
                    )
                    authority = (
                        CandidateAuthority.PREPARATION
                        if relative.parts[0] == "pcs"
                        else CandidateAuthority.NPC_INTENTION
                    )
                    conditional = relative.parts[0] == "pcs"
                elif "possib" in lowered or "question" in lowered or lowered == "notes":
                    state = ClaimState.POSSIBLE
                    authority = CandidateAuthority.BRAINSTORM
                    conditional = False
                else:
                    state = ClaimState.ESTABLISHED
                    authority = CandidateAuthority.EXPLICIT_LORE
                    conditional = False
                candidates.append(
                    _candidate(
                        section,
                        state=state,
                        authority=authority,
                        parser_version=self.config.parser_version,
                        conditional=conditional,
                    )
                )
        else:
            classification = ImportClassification.QUARANTINE
            outcome = ImportOutcome.QUARANTINED

        unresolved = [
            target.strip().casefold()
            for target in WIKI_LINK.findall(text)
            if target.strip().casefold() not in known_targets
        ]
        if unresolved:
            warnings.append(
                ImportWarning.UNRESOLVED_LINK_DIAGNOSTIC_ONLY
                if classification
                in {ImportClassification.TEMPLATE, ImportClassification.NAVIGATION_INDEX}
                else ImportWarning.UNRESOLVED_LINK
            )
        return ScannedSource(
            path=path,
            content_hash=content_hash,
            content=content,
            filesystem_modified_at=modified_at,
            external_id=str(metadata["id"]) if metadata.get("id") else None,
            canonical_name=str(metadata["name"]) if metadata.get("name") else None,
            frontmatter=metadata,
            classification=classification,
            proposed_outcome=outcome,
            candidates=tuple(candidates),
            entity_candidates=entity_candidates,
            warnings=tuple(warnings),
        )


def _classification_conflicts(
    path: PurePosixPath,
    record_type: str,
    status: str,
) -> bool:
    path_kind: str | None = None
    if path.parts[:2] == ("sessions", "notes"):
        path_kind = "real_play"
    elif path == PurePosixPath("gm/campaign-bible.md"):
        path_kind = "planning"
    elif path.parts[:2] == ("gm", "brainstorming"):
        path_kind = "brainstorm"
    elif path.parts[:2] == ("sessions", "prep") or (
        path.parts and path.parts[0] == "encounters"
    ):
        path_kind = "preparation"
    elif path.parts and path.parts[0] in {"npcs", "pcs", "locations", "lore"}:
        path_kind = "durable"

    type_kind: str | None = None
    if record_type == "session-note" or (record_type == "session" and status == "note"):
        type_kind = "real_play"
    elif record_type == "brainstorm":
        type_kind = "brainstorm"
    elif record_type in {"session-prep", "encounter"}:
        type_kind = "preparation"
    elif record_type in {"npc", "pc", "location", "lore"}:
        type_kind = "durable"
    return path_kind is not None and type_kind is not None and path_kind != type_kind


def _evidence_heading(name: str) -> bool:
    lowered = name.casefold()
    return any(
        marker in lowered
        for marker in ("source", "reference", "link", "original biography")
    )


def _read_aloud_heading(name: str) -> bool:
    return "read-aloud" in name.casefold() or "read aloud" in name.casefold()
