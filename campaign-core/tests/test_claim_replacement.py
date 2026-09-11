import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from dm_assistant_core.application.claim_reconciliation import (
    ClaimDateParts,
    ClaimReplacementDraft,
    ReplaceClaimCommand,
)


def replacement(**overrides: object) -> ClaimReplacementDraft:
    values: dict[str, object] = {
        "assertion_text": "Romulus prepared the western seal.",
        "state": "prepared",
        "authority": "preparation",
        "visibility": "dm_only",
    }
    values.update(overrides)
    return ClaimReplacementDraft.model_validate(values)


def test_replacement_command_accepts_independently_classified_split_claims() -> None:
    command = ReplaceClaimCommand(
        claim_id=uuid4(),
        snapshot_hash="a" * 64,
        replacements=(
            replacement(),
            replacement(
                assertion_text="The party observed the opened seal.",
                state="observed",
                authority="real_play",
                observed={"year": 2026, "month": 4, "day": 25},
            ),
        ),
        reason="Separate preparation from real-play outcome.",
        idempotency_key="replace:romulus:mixed",
    )

    assert len(command.replacements) == 2
    assert command.replacements[1].observed == ClaimDateParts(
        year=2026, month=4, day=25
    )


def test_observed_replacement_requires_an_observed_campaign_date() -> None:
    with pytest.raises(ValidationError, match="observed campaign date"):
        replacement(state="observed", authority="real_play")


def test_campaign_date_day_requires_month() -> None:
    with pytest.raises(ValidationError, match="day requires a month"):
        ClaimDateParts(year=2026, day=25)


def test_romulus_campaign_bible_material_splits_by_truth_state() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "romulus_mixed_claim.json").read_text()
    )
    command = ReplaceClaimCommand(
        claim_id=uuid4(), snapshot_hash="b" * 64,
        replacements=tuple(
            ClaimReplacementDraft.model_validate(item)
            for item in fixture["replacements"]
        ),
        reason="Separate established lore from an explicitly possible mechanism.",
        idempotency_key="replace:campaign-bible:romulus",
    )

    assert [item.state.value for item in command.replacements] == [
        "established", "possible", "established"
    ]
    assert fixture["excluded_prompt"] not in {
        item.assertion_text for item in command.replacements
    }
