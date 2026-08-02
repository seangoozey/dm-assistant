"""Test-only reference scanner for sanitized Markdown importer fixtures."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from dm_assistant_core.acceptance.importer_fixtures import (
    ImportClassification,
    ImportOutcome,
    ImportWarning,
    ReconciliationFixture,
    SyntheticScan,
)
from dm_assistant_core.domain import ClaimState, Visibility

INCLUDED_ROOTS = {
    "encounters",
    "gm",
    "handouts",
    "locations",
    "lore",
    "npcs",
    "pcs",
    "sessions",
    "templates",
}
WIKI_LINK = re.compile(r"\[\[([^]|#]+)")


@dataclass(frozen=True)
class Candidate:
    state: ClaimState
    section: str
    visibility: Visibility = Visibility.DM_ONLY
    conditional: bool = False
    predicts_pc_action: bool = False
    evidence_only: bool = False


@dataclass(frozen=True)
class ScannedFile:
    path: str
    content_hash: str
    classification: ImportClassification
    outcome: ImportOutcome
    candidates: tuple[Candidate, ...]
    entity_candidates: int
    warnings: tuple[ImportWarning, ...]
    source_revisions: int = 1
    canonical_mutations: int = 0


@dataclass(frozen=True)
class ScanResult:
    files: tuple[ScannedFile, ...]
    scope_exclusions: tuple[str, ...]


class ReadTracker:
    def __init__(self) -> None:
        self.reads: Counter[str] = Counter()

    def read_bytes(self, root: Path, relative_path: str) -> bytes:
        self.reads[relative_path] += 1
        return (root / Path(relative_path)).read_bytes()


def is_derived_gm_path(relative: PurePosixPath) -> bool:
    return relative == PurePosixPath("gm/location-migration-inventory.md") or (
        len(relative.parts) >= 2 and relative.parts[:2] == ("gm", "location-evidence")
    )


def discover_paths(root: Path) -> tuple[list[str], list[str]]:
    admitted: list[str] = []
    excluded: list[str] = []

    def walk(directory: Path, relative_directory: PurePosixPath) -> None:
        for child in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
            relative = relative_directory / child.name
            relative_text = relative.as_posix()
            if is_derived_gm_path(relative):
                excluded.append(f"{relative_text}/" if child.is_dir() else relative_text)
                continue
            if child.is_dir():
                walk(child, relative)
            elif child.is_file():
                admitted.append(relative_text)

    for child in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not child.is_dir() or child.name not in INCLUDED_ROOTS:
            excluded.append(f"{child.name}/" if child.is_dir() else child.name)
            continue
        walk(child, PurePosixPath(child.name))
    return admitted, excluded


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str, ImportWarning | None]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, ImportWarning.MISSING_FRONTMATTER
    try:
        closing = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration:
        return None, text, ImportWarning.INVALID_FRONTMATTER
    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError:
        return None, "\n".join(lines[closing + 1 :]), ImportWarning.INVALID_FRONTMATTER
    if not isinstance(frontmatter, dict):
        return None, "\n".join(lines[closing + 1 :]), ImportWarning.INVALID_FRONTMATTER
    return frontmatter, "\n".join(lines[closing + 1 :]), None


def heading_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line.removeprefix("## ").strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def has_content(sections: dict[str, str], section: str) -> bool:
    content = sections.get(section, "").strip()
    return bool(content and "[Not yet established.]" not in content)


def planning_candidates(body: str) -> tuple[Candidate, ...]:
    heading = re.compile(r"^(#{2,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)
    matches = list(heading.finditer(body))
    ancestors: list[tuple[int, str]] = []
    candidates: list[Candidate] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        while ancestors and ancestors[-1][0] >= level:
            ancestors.pop()
        content_start = match.end()
        if content_start < len(body) and body[content_start] in "\r\n":
            content_start += 2 if body[content_start : content_start + 2] == "\r\n" else 1
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[content_start:content_end].strip()
        path = " / ".join([value for _ancestor_level, value in ancestors] + [title])
        lowered = title.casefold()
        if content and "reference" not in lowered and lowered != "overview":
            if any(marker in lowered for marker in ("prepared", "pressure", "scenario")):
                state = ClaimState.PREPARED
            elif any(marker in lowered for marker in ("intent", "plan", "goal", "objective")):
                state = ClaimState.INTENDED
            else:
                state = ClaimState.POSSIBLE
            candidates.append(Candidate(state=state, section=path))
        ancestors.append((level, title))
    return tuple(candidates)


def classify_and_extract(
    path: str,
    text: str,
    known_targets: set[str],
) -> tuple[
    ImportClassification,
    ImportOutcome,
    tuple[Candidate, ...],
    int,
    tuple[ImportWarning, ...],
]:
    relative = PurePosixPath(path)
    warnings: list[ImportWarning] = []
    if relative.suffix.casefold() != ".md":
        return (
            ImportClassification.QUARANTINE,
            ImportOutcome.QUARANTINED,
            (),
            0,
            (ImportWarning.UNKNOWN_FORMAT,),
        )

    frontmatter, body, frontmatter_warning = parse_frontmatter(text)
    metadata = frontmatter or {}
    if frontmatter_warning is not None:
        warnings.append(frontmatter_warning)
    record_type = str(metadata.get("type", ""))
    status = str(metadata.get("status", ""))
    sections = heading_sections(body)

    if relative.parts[0] == "templates":
        classification = ImportClassification.TEMPLATE
        outcome = ImportOutcome.TEMPLATE_EXCLUDED
        candidates: tuple[Candidate, ...] = ()
        entity_candidates = 0
    elif relative.name == "00_index.md" or record_type.endswith("-index"):
        classification = ImportClassification.NAVIGATION_INDEX
        outcome = ImportOutcome.NAVIGATION_EXCLUDED
        candidates = ()
        entity_candidates = 0
    elif relative.parts[:2] == ("sessions", "notes"):
        classification = ImportClassification.REAL_PLAY_EVIDENCE
        outcome = ImportOutcome.NEW
        if record_type == "session" and status == "note":
            warnings.append(ImportWarning.LEGACY_SESSION_METADATA)
        if status == "needs-review" and has_content(sections, "Canon Deltas"):
            warnings.append(ImportWarning.UNRESOLVED_CANON_DELTAS)
        if status == "applied-delta" and has_content(sections, "Canon Deltas"):
            warnings.append(ImportWarning.APPLIED_DELTA_NO_REAPPLY)
        candidates = (
            (Candidate(state=ClaimState.OBSERVED, section="Observed Events"),)
            if has_content(sections, "Observed Events")
            else ()
        )
        entity_candidates = 0
    elif record_type == "session" and status == "note":
        classification = ImportClassification.QUARANTINE
        outcome = ImportOutcome.QUARANTINED
        warnings.append(ImportWarning.LEGACY_SESSION_WRONG_PATH)
        candidates = ()
        entity_candidates = 0
    elif path == "gm/campaign-bible.md":
        classification = ImportClassification.PLANNING_EVIDENCE
        outcome = ImportOutcome.REVIEW_REQUIRED
        candidates = planning_candidates(body)
        entity_candidates = 0
    elif relative.parts[:2] == ("gm", "brainstorming") or record_type == "brainstorm":
        classification = ImportClassification.NONCANON_EVIDENCE
        outcome = ImportOutcome.NEW
        if has_content(sections, "Promotion Receipt"):
            warnings.append(ImportWarning.PROMOTION_RECEIPT_NO_REAPPLY)
        candidates = ()
        entity_candidates = 0
    elif relative.parts[:2] == ("sessions", "prep") or record_type == "session-prep":
        classification = ImportClassification.PLANNED_PREPARATION
        outcome = ImportOutcome.NEW
        candidates = tuple(
            candidate
            for candidate, section in (
                (
                    Candidate(
                        state=ClaimState.OBSERVED,
                        section="Recap",
                        evidence_only=True,
                    ),
                    "Recap",
                ),
                (
                    Candidate(state=ClaimState.PREPARED, section="Expected Outcomes"),
                    "Expected Outcomes",
                ),
            )
            if has_content(sections, section)
        )
        entity_candidates = 0
    elif relative.parts[0] == "encounters" or record_type == "encounter":
        classification = ImportClassification.PREPARATION
        outcome = ImportOutcome.NEW
        candidates = (
            (Candidate(state=ClaimState.PREPARED, section="Prepared Scenario"),)
            if has_content(sections, "Prepared Scenario")
            else ()
        )
        if has_content(sections, "Read Aloud"):
            warnings.append(ImportWarning.READ_ALOUD_IS_DERIVED)
        entity_candidates = 0
    elif (
        relative.parts[0] in {"npcs", "pcs", "locations", "lore"}
        and status == "canon"
        and record_type in {"npc", "pc", "location", "lore"}
    ):
        classification = ImportClassification.DURABLE_EVIDENCE
        outcome = ImportOutcome.NEW
        extracted: list[Candidate] = []
        if has_content(sections, "Established Facts"):
            extracted.append(Candidate(state=ClaimState.ESTABLISHED, section="Established Facts"))
        if has_content(sections, "Current Goals"):
            extracted.append(Candidate(state=ClaimState.INTENDED, section="Current Goals"))
        if has_content(sections, "Possibilities"):
            extracted.append(Candidate(state=ClaimState.POSSIBLE, section="Possibilities"))
        if has_content(sections, "Private GM Notes"):
            extracted.append(
                Candidate(
                    state=ClaimState.PREPARED,
                    section="Private GM Notes",
                    conditional=True,
                    predicts_pc_action=False,
                )
            )
        candidates = tuple(extracted)
        entity_candidates = 1
    else:
        classification = ImportClassification.QUARANTINE
        outcome = ImportOutcome.QUARANTINED
        candidates = ()
        entity_candidates = 0

    unresolved = [
        target.strip().casefold()
        for target in WIKI_LINK.findall(text)
        if target.strip().casefold() not in known_targets
    ]
    if unresolved:
        if classification in {
            ImportClassification.TEMPLATE,
            ImportClassification.NAVIGATION_INDEX,
        }:
            warnings.append(ImportWarning.UNRESOLVED_LINK_DIAGNOSTIC_ONLY)
        else:
            warnings.append(ImportWarning.UNRESOLVED_LINK)

    return classification, outcome, candidates, entity_candidates, tuple(warnings)


def scan_fixture(root: Path, tracker: ReadTracker) -> ScanResult:
    admitted, exclusions = discover_paths(root)
    known_targets = {
        PurePosixPath(path).stem.casefold()
        for path in admitted
        if PurePosixPath(path).suffix.casefold() == ".md"
    }
    records: list[ScannedFile] = []
    for path in admitted:
        content = tracker.read_bytes(root, path)
        text = content.decode("utf-8")
        classification, outcome, candidates, entity_candidates, warnings = classify_and_extract(
            path,
            text,
            known_targets,
        )
        records.append(
            ScannedFile(
                path=path,
                content_hash=sha256(content).hexdigest(),
                classification=classification,
                outcome=outcome,
                candidates=candidates,
                entity_candidates=entity_candidates,
                warnings=warnings,
            )
        )
    return ScanResult(files=tuple(records), scope_exclusions=tuple(exclusions))


@dataclass
class SourceDocumentState:
    stable_id: str
    current_path: str
    paths: set[str] = field(default_factory=set)
    hashes: list[str] = field(default_factory=list)
    candidates: set[str] = field(default_factory=set)
    canonical_truth: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class ReconciliationResult:
    outcomes: tuple[ImportOutcome, ...]
    source_documents: int
    source_revisions: int
    candidates: int
    canonical_truth: int


class ReconciliationStore:
    def __init__(self, fixture: ReconciliationFixture) -> None:
        self.confirmation_threshold = fixture.confirmation_threshold
        self.documents: dict[str, SourceDocumentState] = {}

    def scan(self, scan: SyntheticScan) -> ReconciliationResult:
        outcomes: list[ImportOutcome] = []
        present_ids: set[str] = set()
        for source in scan.files:
            present_ids.add(source.stable_id)
            content_hash = sha256(source.content.encode("utf-8")).hexdigest()
            document = self.documents.get(source.stable_id)
            if document is None:
                document = SourceDocumentState(
                    stable_id=source.stable_id,
                    current_path=source.path,
                    paths={source.path},
                    hashes=[content_hash],
                    candidates={content_hash},
                    canonical_truth={content_hash},
                )
                self.documents[source.stable_id] = document
                outcomes.append(ImportOutcome.NEW)
            elif source.path != document.current_path and content_hash == document.hashes[-1]:
                document.current_path = source.path
                document.paths.add(source.path)
                outcomes.append(ImportOutcome.MOVED)
            elif content_hash == document.hashes[-1]:
                outcomes.append(ImportOutcome.UNCHANGED)
            else:
                document.current_path = source.path
                document.paths.add(source.path)
                document.hashes.append(content_hash)
                document.candidates.add(content_hash)
                document.canonical_truth.add(content_hash)
                outcomes.append(ImportOutcome.CHANGED)

        for _stable_id in self.documents.keys() - present_ids:
            if self.confirmation_threshold == 1:
                outcomes.append(ImportOutcome.MISSING_SOURCE)

        return ReconciliationResult(
            outcomes=tuple(outcomes),
            source_documents=len(self.documents),
            source_revisions=sum(len(document.hashes) for document in self.documents.values()),
            candidates=sum(len(document.candidates) for document in self.documents.values()),
            canonical_truth=sum(
                len(document.canonical_truth) for document in self.documents.values()
            ),
        )
