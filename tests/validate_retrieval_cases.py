"""Standalone structural validation for the grounded retrieval corpus."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "retrieval_cases.yaml"
REQUIRED_CATEGORIES = {
    "direct_fact",
    "alias",
    "relationship",
    "chronology",
    "contradiction",
    "noncanon_leakage",
    "unknown",
    "character_visibility",
    "recent_update",
}
ANSWER_MODES = {
    "answer",
    "insufficient_evidence",
    "conflict",
    "possible_retcon",
    "restricted",
}
ORIGINS = {"sanitized_starfall_derived", "synthetic_behavioral"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_nonempty_list(value: Any, label: str) -> None:
    require(isinstance(value, list) and bool(value), f"{label} must be a non-empty list")


def validate_record(record: Any, label: str) -> None:
    require(isinstance(record, dict), f"{label} must be an object")
    for field in ("record_id", "kind", "assertion", "state", "authority", "visibility", "source_id", "citation"):
        require(isinstance(record.get(field), str) and bool(record[field]), f"{label}.{field} is required")


def validate_case(case: Any, seen_ids: set[str]) -> None:
    require(isinstance(case, dict), "each case must be an object")
    case_id = case.get("id")
    require(isinstance(case_id, str) and bool(case_id), "case.id is required")
    require(case_id not in seen_ids, f"duplicate case id: {case_id}")
    seen_ids.add(case_id)

    require(case.get("category") in REQUIRED_CATEGORIES, f"{case_id}: unknown category")
    require(case.get("fixture_origin") in ORIGINS, f"{case_id}: unknown fixture_origin")
    require(isinstance(case.get("question"), str) and bool(case["question"]), f"{case_id}: question is required")

    visibility = case.get("requester_visibility")
    require(isinstance(visibility, dict), f"{case_id}: requester_visibility is required")
    require(visibility.get("role") in {"dm", "party", "character"}, f"{case_id}: invalid requester role")
    if visibility["role"] == "character":
        require(isinstance(visibility.get("character_id"), str), f"{case_id}: character_id is required")

    for field in ("authoritative_inputs", "context_inputs"):
        records = case.get(field)
        require(isinstance(records, list), f"{case_id}: {field} must be a list")
        for index, record in enumerate(records):
            validate_record(record, f"{case_id}.{field}[{index}]")

    expected = case.get("expected")
    require(isinstance(expected, dict), f"{case_id}: expected is required")
    require(expected.get("answer_mode") in ANSWER_MODES, f"{case_id}: invalid answer_mode")
    require_nonempty_list(expected.get("facts"), f"{case_id}.expected.facts")
    require(isinstance(expected.get("required_citations"), list), f"{case_id}.expected.required_citations must be a list")
    require_nonempty_list(expected.get("forbidden_claims"), f"{case_id}.expected.forbidden_claims")


def main() -> None:
    data = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "fixture root must be an object")
    require(data.get("schema_version") == 1, "schema_version must be 1")
    source_policy = data.get("source_policy")
    require(isinstance(source_policy, dict), "source_policy is required")
    require(source_policy.get("live_source_accessed") is False, "corpus must not claim live-source access")

    cases = data.get("cases")
    require(isinstance(cases, list), "cases must be a list")
    require(30 <= len(cases) <= 50, "suite must contain between 30 and 50 cases")

    seen_ids: set[str] = set()
    for case in cases:
        validate_case(case, seen_ids)

    categories = Counter(case["category"] for case in cases)
    modes = Counter(case["expected"]["answer_mode"] for case in cases)
    require(REQUIRED_CATEGORIES <= categories.keys(), "suite does not cover every required category")
    require(categories["unknown"] >= 5, "suite requires at least five unknown cases")
    require(categories["noncanon_leakage"] >= 5, "suite requires at least five non-canon leakage cases")
    require(modes["conflict"] + modes["possible_retcon"] >= 3, "suite requires at least three conflict/retcon cases")
    require(categories["chronology"] >= 3, "suite requires at least three chronology cases")

    category_summary = ", ".join(f"{name}={count}" for name, count in sorted(categories.items()))
    mode_summary = ", ".join(f"{name}={count}" for name, count in sorted(modes.items()))
    print(f"Validated {len(cases)} retrieval cases.")
    print(f"Categories: {category_summary}")
    print(f"Answer modes: {mode_summary}")


if __name__ == "__main__":
    main()
