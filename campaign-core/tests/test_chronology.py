from __future__ import annotations

import pytest
from pydantic import ValidationError

from dm_assistant_core.domain.chronology import (
    CALENDAR,
    CURRENT_CAMPAIGN_YEAR,
    GREGORIAN_CE,
    CalendarSpecError,
    CampaignDate,
    compare_same_calendar,
    resolve_relative_year,
)


class TestCampaignDate:
    def test_ce_year_stores_and_renders(self) -> None:
        date = CampaignDate(year=505, month=11, day=26)
        assert date.year == 505
        assert date.is_complete()

    def test_bce_year_stores_as_negative_integer(self) -> None:
        date = CampaignDate(year=-20000)
        assert date.year == -20000
        assert not date.is_complete()

    def test_undated_record_is_valid(self) -> None:
        date = CampaignDate()
        assert date.year is None
        assert date.day_ordinal() is None

    def test_year_only_partial_date(self) -> None:
        date = CampaignDate(year=347)
        assert date.day_ordinal() is None

    def test_day_requires_month(self) -> None:
        with pytest.raises(ValidationError):
            CampaignDate(year=505, day=15)

    def test_impossible_day_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CampaignDate(year=505, month=2, day=30)

    def test_leap_day_accepted(self) -> None:
        date = CampaignDate(year=504, month=2, day=29)  # 504 is divisible by 4
        assert date.is_complete()

    def test_non_leap_february_29_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CampaignDate(year=505, month=2, day=29)

    def test_unsupported_calendar_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CampaignDate(calendar_id="elven", year=505)

    def test_calendar_id_defaults_to_gregorian_ce(self) -> None:
        assert CampaignDate(year=505).calendar_id == GREGORIAN_CE

    def test_invalid_month_rejected_by_pydantic(self) -> None:
        with pytest.raises(ValidationError):
            CampaignDate(year=505, month=13)


class TestDayOrdinal:
    def test_one_month_apart(self) -> None:
        early = CampaignDate(year=505, month=6, day=20)
        late = CampaignDate(year=505, month=7, day=20)
        assert late.day_ordinal() is not None
        assert early.day_ordinal() is not None
        assert late.day_ordinal() - early.day_ordinal() == 30  # June has 30 days

    def test_year_apart(self) -> None:
        # June 20, 504 to June 20, 505. Feb 29, 504 has already passed by June,
        # and 505 is not a leap year, so the span is exactly 365 days.
        year_504 = CampaignDate(year=504, month=6, day=20)
        year_505 = CampaignDate(year=505, month=6, day=20)
        diff = year_505.day_ordinal() - year_504.day_ordinal()  # type: ignore[operator]
        assert diff == 365

    def test_year_span_crossing_leap_day(self) -> None:
        # Jan 1, 504 to Jan 1, 505 crosses Feb 29, 504 (504 is a leap year): 366 days.
        start = CampaignDate(year=504, month=1, day=1)
        end = CampaignDate(year=505, month=1, day=1)
        diff = end.day_ordinal() - start.day_ordinal()  # type: ignore[operator]
        assert diff == 366

    def test_bce_orders_before_ce(self) -> None:
        bce = CampaignDate(year=-20000, month=1, day=1)
        ce = CampaignDate(year=505, month=1, day=1)
        assert bce.day_ordinal() < ce.day_ordinal()


class TestComparison:
    def test_same_calendar_orders_by_year(self) -> None:
        early = CampaignDate(year=400)
        late = CampaignDate(year=505)
        assert compare_same_calendar(early, late) < 0
        assert compare_same_calendar(late, early) > 0

    def test_equal_dates_compare_zero(self) -> None:
        assert compare_same_calendar(CampaignDate(year=505), CampaignDate(year=505)) == 0

    def test_partial_date_compares_by_available_components(self) -> None:
        year_only = CampaignDate(year=505)
        full = CampaignDate(year=505, month=6, day=1)
        assert compare_same_calendar(year_only, full) < 0


class TestRelativeYear:
    def test_negative_offset_resolves_against_anchor(self) -> None:
        assert resolve_relative_year(-220) == 285
        assert resolve_relative_year(-220, anchor_year=505) == 285

    def test_explicit_anchor(self) -> None:
        assert resolve_relative_year(-200, anchor_year=1500) == 1300

    def test_positive_offset_rejected(self) -> None:
        with pytest.raises(CalendarSpecError):
            resolve_relative_year(5)

    def test_current_campaign_year_is_505(self) -> None:
        assert CURRENT_CAMPAIGN_YEAR == 505


class TestCalendarSpec:
    def test_gregorian_months(self) -> None:
        assert CALENDAR.months_in_year == 12
        assert CALENDAR.days_in_year == 365
        assert CALENDAR.month(2).name == "February"

    def test_leap_year_detection(self) -> None:
        assert CALENDAR.is_leap_year(504) is True
        assert CALENDAR.is_leap_year(505) is False
        assert CALENDAR.is_leap_year(400) is True
        assert CALENDAR.is_leap_year(100) is False

    def test_days_in_month_accounts_for_leap(self) -> None:
        assert CALENDAR.days_in_month(504, 2) == 29
        assert CALENDAR.days_in_month(505, 2) == 28
