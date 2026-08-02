from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from dm_assistant_core.acceptance import DeterministicAssertion, InteractionFixture
from tests.support.interaction_harness import (
    FIXTURE_PATH,
    execute_deterministic_assertions,
    load_interaction_fixture,
)

FIXTURE = load_interaction_fixture()
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def load_raw_fixture() -> dict[str, Any]:
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


def ticket_ids() -> set[str]:
    ids: set[str] = set()
    for path in (REPOSITORY_ROOT / "tickets").rglob("*.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("id: "):
                ids.add(line.removeprefix("id: "))
                break
    return ids


def test_every_interaction_case_is_typed() -> None:
    assert FIXTURE.schema_version == 2
    assert len(FIXTURE.cases) == 9


def test_every_assertion_type_has_a_registered_runner() -> None:
    from tests.support.interaction_harness import ASSERTION_RUNNERS

    assert set(ASSERTION_RUNNERS) == set(DeterministicAssertion)


def test_required_domain_scenarios_are_executable() -> None:
    executable = {
        assertion
        for case in FIXTURE.cases
        for assertion in case.deterministic_assertions
    }
    assert {
        DeterministicAssertion.APPROVAL_SCOPE_IS_EXACT,
        DeterministicAssertion.APPROVAL_BINDS_TO_CURRENT_VERSION,
        DeterministicAssertion.PC_DIRECTION_IS_CONDITIONAL,
        DeterministicAssertion.OBSERVED_SUPERSEDES_PREPARED,
    } <= executable


@pytest.mark.parametrize(
    "case",
    [case for case in FIXTURE.cases if case.deterministic_assertions],
    ids=lambda case: case.id,
)
def test_registered_fixture_assertions_execute(case: Any) -> None:
    assert execute_deterministic_assertions(case) == len(case.deterministic_assertions)


def test_core_cases_are_executable_or_have_a_real_ticket_dependency() -> None:
    known_tickets = ticket_ids()
    for case in FIXTURE.cases:
        if not case.enforcement.includes_core:
            continue
        assert case.deterministic_assertions or case.implementation_dependency
        if case.implementation_dependency:
            assert case.implementation_dependency in known_tickets


def test_mixed_cases_separate_deferred_evaluations() -> None:
    mixed = [case for case in FIXTURE.cases if "_and_" in case.enforcement.value]
    assert mixed
    assert all(case.deferred_evaluations for case in mixed)


def test_execution_is_order_independent() -> None:
    forward = {
        case.id: execute_deterministic_assertions(case)
        for case in FIXTURE.cases
        if case.deterministic_assertions
    }
    reverse = {
        case.id: execute_deterministic_assertions(case)
        for case in reversed(FIXTURE.cases)
        if case.deterministic_assertions
    }
    assert forward == reverse


@pytest.mark.parametrize(
    ("mutate", "expected_messages"),
    [
        (
            lambda raw: raw["cases"][0].pop("input"),
            ("input", "Field required"),
        ),
        (
            lambda raw: raw["cases"].append(deepcopy(raw["cases"][0])),
            ("duplicate interaction case IDs",),
        ),
        (
            lambda raw: raw["cases"][0].update({"expected_output": []}),
            ("expected_output", "at least 1 item"),
        ),
        (
            lambda raw: raw["cases"][0].update({"active_workflow": "unknown_workflow"}),
            ("active_workflow", "Input should be"),
        ),
        (
            lambda raw: raw["cases"][0].update({"enforcement": "unknown_owner"}),
            ("enforcement", "Input should be"),
        ),
    ],
    ids=["missing-field", "duplicate-id", "empty-list", "unknown-workflow", "unknown-owner"],
)
def test_invalid_fixture_reports_actionable_errors(
    mutate: Any,
    expected_messages: tuple[str, ...],
) -> None:
    raw = load_raw_fixture()
    mutate(raw)

    with pytest.raises(ValidationError) as error:
        InteractionFixture.model_validate(raw)

    message = str(error.value)
    for expected in expected_messages:
        assert expected in message
