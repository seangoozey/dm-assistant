"""Path-aware wiki-link target resolution.

Wiki links are Obsidian-style file references of the form ``[[target]]``. The
target names a source document by its relative path; Obsidian drops the ``.md``
extension, so ``[[lore/medallions]]`` references ``lore/medallions.md``. A
display alias (``[[target|Label]]``) and fragment (``[[target#Section]]``) are
bound to the same target and never change which file is referenced.

The bracket target is authoritative. A path-qualified link resolves only to the
exact admitted file it names; it is never rescued onto a same-named file in
another directory. A bare link (no directory) resolves to its basename when
exactly one admitted file shares that stem, reports an explicit ambiguous
diagnostic when more than one does, and stays unresolved otherwise. Templates
and navigation indexes are scaffolds and index pages, not records a link may
resolve onto, so they are excluded as targets; links originating from them
remain source diagnostics.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath


class LinkTargetStatus(StrEnum):
    """The resolution outcome for a single wiki-link target."""

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"


@dataclass(frozen=True)
class LinkIndex:
    """Admitted source paths that wiki links may resolve onto.

    ``paths`` holds casefolded normalized relative POSIX paths (without the
    ``.md`` extension) for admitted record files. ``stem_counts`` holds the
    multiplicity of each basename stem so a bare link can detect ambiguity.
    """

    paths: frozenset[str]
    stem_counts: Counter[str]

    @classmethod
    def empty(cls) -> LinkIndex:
        return cls(paths=frozenset(), stem_counts=Counter())

    @classmethod
    def build(cls, admitted_paths: set[str] | frozenset[str]) -> LinkIndex:
        normalized = {
            _normalize_admitted_path(path)
            for path in admitted_paths
            if PurePosixPath(path).suffix.casefold() == ".md"
        }
        stem_counts: Counter[str] = Counter()
        for path in normalized:
            stem_counts[PurePosixPath(path).stem.casefold()] += 1
        return cls(paths=frozenset(normalized), stem_counts=stem_counts)


@dataclass(frozen=True)
class LinkTarget:
    """The normalized target string and its resolution status."""

    target: str
    status: LinkTargetStatus


def _normalize_admitted_path(path: str) -> str:
    """Return a casefolded relative POSIX path without its ``.md`` extension."""

    posix = path.replace("\\", "/")
    relative = posix[2:] if posix.startswith("./") else posix
    stem = PurePosixPath(relative)
    without_suffix = stem.with_suffix("") if stem.suffix.casefold() == ".md" else stem
    return without_suffix.as_posix().casefold()


def normalize_target(target: str, *, source_path: str) -> str:
    """Normalize a wiki-link target into the index key space.

    Backslashes become POSIX separators, a leading ``./`` is stripped, and an
    optional ``.md`` suffix is dropped. A relative target (``./`` or ``../``) is
    resolved against the directory of ``source_path``; any other target is taken
    as root-relative. The result is casefolded so comparison is
    case-insensitive, mirroring Obsidian's default vault behavior.
    """

    posix = target.strip().replace("\\", "/")
    if not posix:
        return posix
    has_suffix = posix.casefold().endswith(".md")
    if has_suffix:
        posix = posix[: -len(".md")]
    if posix.startswith(("./", "../")):
        base = PurePosixPath(source_path.replace("\\", "/")).parent
        normalized = _resolve_relative(base, posix).as_posix()
    else:
        normalized = posix[2:] if posix.startswith("./") else posix
    return PurePosixPath(normalized).as_posix().casefold()


def _resolve_relative(base: PurePosixPath, relative: str) -> PurePosixPath:
    """Resolve ``relative`` against ``base`` without filesystem access."""

    parts: list[str] = []
    parts.extend(base.parts)
    for component in PurePosixPath(relative).parts:
        if component == ".":
            continue
        if component == "..":
            if parts:
                parts.pop()
            continue
        parts.append(component)
    return PurePosixPath(*parts) if parts else PurePosixPath()


def classify_target(target: str, index: LinkIndex, *, source_path: str) -> LinkTarget:
    """Classify a single raw wiki-link target against the index.

    Path-qualified targets match the exact admitted path only; a bare target
    matches by basename stem and reports ambiguity when more than one admitted
    file shares it.
    """

    normalized = normalize_target(target, source_path=source_path)
    if not normalized:
        return LinkTarget(target=normalized, status=LinkTargetStatus.MISSING)
    if "/" in normalized:
        status = (
            LinkTargetStatus.RESOLVED if normalized in index.paths else LinkTargetStatus.MISSING
        )
        return LinkTarget(target=normalized, status=status)
    count = index.stem_counts.get(normalized, 0)
    if count == 1:
        return LinkTarget(target=normalized, status=LinkTargetStatus.RESOLVED)
    if count > 1:
        return LinkTarget(target=normalized, status=LinkTargetStatus.AMBIGUOUS)
    return LinkTarget(target=normalized, status=LinkTargetStatus.MISSING)


def classify_targets(
    targets: set[str] | list[str] | tuple[str, ...],
    index: LinkIndex,
    *,
    source_path: str,
) -> list[LinkTarget]:
    """Classify a collection of raw wiki-link targets, preserving input order."""

    return [classify_target(target, index, source_path=source_path) for target in targets]
