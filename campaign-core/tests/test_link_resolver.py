from __future__ import annotations

from dm_assistant_core.importer.links import (
    LinkIndex,
    LinkTargetStatus,
    classify_target,
    normalize_target,
)


def index(paths: set[str]) -> LinkIndex:
    return LinkIndex.build(paths)


def status(
    target: str,
    idx: LinkIndex,
    *,
    source: str = "gm/campaign-bible.md",
) -> LinkTargetStatus:
    return classify_target(target, idx, source_path=source).status


class TestPathQualifiedResolution:
    def test_exact_path_resolves_without_extension(self) -> None:
        idx = index({"lore/medallions.md", "npcs/ishigo-dan.md"})

        assert status("lore/medallions", idx) is LinkTargetStatus.RESOLVED

    def test_explicit_md_suffix_resolves(self) -> None:
        idx = index({"lore/medallions.md"})

        assert status("lore/medallions.md", idx) is LinkTargetStatus.RESOLVED

    def test_nested_subdirectory_path_resolves(self) -> None:
        idx = index({"locations/illisan/fleurite/fleurite.md"})

        assert status("locations/illisan/fleurite/fleurite", idx) is LinkTargetStatus.RESOLVED

    def test_path_qualified_to_wrong_directory_is_missing(self) -> None:
        idx = index({"lore/medallions.md"})

        # A same-named file in a different directory must never be rescued.
        assert status("npcs/medallions", idx) is LinkTargetStatus.MISSING
        assert status("encounters/medallions", idx) is LinkTargetStatus.MISSING

    def test_truly_dead_path_qualified_link_is_missing(self) -> None:
        idx = index({"lore/medallions.md"})

        assert status("lore/totally-absent", idx) is LinkTargetStatus.MISSING

    def test_case_insensitive_path_match(self) -> None:
        idx = index({"lore/Medallions-of-the-Golden-Dawn.md"})

        assert status("lore/medallions-of-the-golden-dawn", idx) is LinkTargetStatus.RESOLVED
        assert status("LORE/MEDALLIONS-OF-THE-GOLDEN-DAWN", idx) is LinkTargetStatus.RESOLVED

    def test_backslash_separator_is_normalized(self) -> None:
        idx = index({"lore/medallions.md"})

        assert status("lore\\medallions", idx) is LinkTargetStatus.RESOLVED


class TestBasenameResolution:
    def test_unique_bare_stem_resolves(self) -> None:
        idx = index({"sessions/notes/reviewed.md", "lore/other.md"})

        assert status("reviewed", idx) is LinkTargetStatus.RESOLVED

    def test_ambiguous_bare_stem_is_ambiguous(self) -> None:
        idx = index({"npcs/shared-vault.md", "locations/shared-vault.md"})

        assert status("shared-vault", idx) is LinkTargetStatus.AMBIGUOUS

    def test_unknown_bare_stem_is_missing(self) -> None:
        idx = index({"npcs/shared-vault.md"})

        assert status("nonexistent", idx) is LinkTargetStatus.MISSING

    def test_three_way_ambiguity_is_still_ambiguous(self) -> None:
        idx = index(
            {
                "npcs/shared-vault.md",
                "locations/shared-vault.md",
                "lore/shared-vault.md",
            }
        )

        assert status("shared-vault", idx) is LinkTargetStatus.AMBIGUOUS


class TestRelativeTargets:
    def test_dot_slash_resolves_relative_to_source_directory(self) -> None:
        idx = index({"gm/brainstorming/neighbor.md"})

        assert (
            status("./neighbor", idx, source="gm/brainstorming/notes.md")
            is LinkTargetStatus.RESOLVED
        )

    def test_dot_dot_resolves_relative_to_source_directory(self) -> None:
        idx = index({"npcs/mixed-npc.md"})

        # From locations/example-location.md, ../npcs/mixed-npc reaches the NPC.
        assert (
            status("../npcs/mixed-npc", idx, source="locations/example-location.md")
            is LinkTargetStatus.RESOLVED
        )

    def test_relative_into_wrong_place_is_missing(self) -> None:
        idx = index({"lore/something.md"})

        assert (
            status("../npcs/absent", idx, source="locations/example-location.md")
            is LinkTargetStatus.MISSING
        )


class TestNormalization:
    def test_empty_target_is_missing(self) -> None:
        idx = index({"lore/medallions.md"})

        assert classify_target("   ", idx, source_path="gm/campaign-bible.md").status is (
            LinkTargetStatus.MISSING
        )

    def test_leading_dot_slash_is_relative_to_source_directory(self) -> None:
        idx = index({"gm/brainstorming/neighbor.md", "lore/medallions.md"})

        # ./lore/medallions from gm/ resolves to gm/lore/medallions, which is absent.
        assert status("./lore/medallions", idx, source="gm/campaign-bible.md") is (
            LinkTargetStatus.MISSING
        )
        # ./neighbor from a doc in gm/brainstorming/ resolves to a sibling.
        assert (
            status("./neighbor", idx, source="gm/brainstorming/notes.md")
            is LinkTargetStatus.RESOLVED
        )

    def test_normalize_target_drops_md_suffix(self) -> None:
        assert normalize_target("lore/Medallions.md", source_path="gm/campaign-bible.md") == (
            "lore/medallions"
        )

    def test_normalize_target_lowercases(self) -> None:
        assert normalize_target("Lore/Medallions", source_path="gm/campaign-bible.md") == (
            "lore/medallions"
        )


class TestIndexConstruction:
    def test_non_markdown_files_are_excluded_as_targets(self) -> None:
        idx = index({"lore/text.txt", "lore/real.md"})

        # The .txt file never enters the path or stem index.
        assert status("lore/text", idx) is LinkTargetStatus.MISSING
        assert status("lore/text.txt", idx) is LinkTargetStatus.MISSING
        assert status("real", idx) is LinkTargetStatus.RESOLVED

    def test_empty_index_reports_everything_missing(self) -> None:
        idx = LinkIndex.empty()

        assert status("anything", idx) is LinkTargetStatus.MISSING
        assert status("lore/anything", idx) is LinkTargetStatus.MISSING

    def test_admitted_path_md_suffix_dropped_in_index(self) -> None:
        idx = index({"lore/Medallions.md"})

        assert "lore/medallions" in idx.paths
        assert idx.stem_counts["medallions"] == 1
