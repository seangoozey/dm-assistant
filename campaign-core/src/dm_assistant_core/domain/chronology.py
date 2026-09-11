"""Campaign chronology: integer-year dates backed by a calendar spec.

Real-world audit instants and in-game campaign chronology are distinct types (ADR-0007).
Audit instants remain UTC ``timestamptz`` at the persistence boundary. Campaign chronology
is stored as integer year/month/day components plus a ``calendar_id`` referencing a
hardcoded calendar spec. A BCE value is a negative integer, with no storage cliff.

Day-arithmetic and ordering are valid only within one calendar. Two records under
different calendars are never silently ordered or subtracted as if directly comparable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: The calendar identity carried by every dated campaign record in v1.
GREGORIAN_CE = "gregorian-ce"

#: The campaign's current in-game year, used as the explicit anchor when resolving
#: legacy relative-year shorthand (``-N``) once. Advancing the campaign year never
#: recalculates an already-stored absolute year.
CURRENT_CAMPAIGN_YEAR = 505


class CalendarSpecError(ValueError):
    """A calendar value is impossible or mixes calendars illegally."""


@dataclass(frozen=True)
class MonthSpec:
    """One month of a hardcoded calendar spec."""

    index: int
    name: str
    days: int


@dataclass(frozen=True)
class CalendarSpec:
    """A hardcoded, durable calendar definition enabling same-calendar day arithmetic.

    A future version may let a DM manage calendars; v1 ships the Gregorian spec only.
    """

    calendar_id: str
    era_label: str
    months: tuple[MonthSpec, ...]
    leap_rule: str
    spec_version: str

    @property
    def months_in_year(self) -> int:
        return len(self.months)

    @property
    def days_in_year(self) -> int:
        return sum(month.days for month in self.months)

    def month(self, index: int) -> MonthSpec:
        if index < 1 or index > self.months_in_year:
            raise CalendarSpecError(f"month {index} is out of range for {self.calendar_id}")
        return self.months[index - 1]

    def is_leap_year(self, year: int) -> bool:
        if self.calendar_id != GREGORIAN_CE:
            return False
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def days_in_month(self, year: int, month: int) -> int:
        base = self.month(month).days
        if self.calendar_id == GREGORIAN_CE and month == 2 and self.is_leap_year(year):
            return base + 1
        return base

    def day_ordinal(self, year: int, month: int | None, day: int | None) -> int | None:
        """A deterministic same-calendar day count anchored at year 0.

        Returns ``None`` for partial dates without month/day. The result is only
        meaningful within this calendar; subtracting ordinals from different
        calendars is never valid.
        """
        if month is None or day is None:
            return None
        self._require_valid(year, month, day)
        cumulative = sum(self.months[m - 1].days for m in range(1, month))
        # Leap days for completed years strictly before this one (Gregorian rule),
        # plus the current year's leap day when past February.
        leap_days_before = self._leap_days_before(year)
        leap_extra = 1 if self.is_leap_year(year) and month > 2 else 0
        return year * self.days_in_year + leap_days_before + cumulative + day + leap_extra

    @staticmethod
    def _leap_days_before(year: int) -> int:
        """Count Gregorian leap days in years strictly before ``year`` (>= 0)."""
        if year <= 0:
            return 0
        end = year - 1
        return end // 4 - end // 100 + end // 400

    def _require_valid(self, year: int, month: int, day: int) -> None:
        if month < 1 or month > self.months_in_year:
            raise CalendarSpecError(f"month {month} is out of range for {self.calendar_id}")
        max_day = self.days_in_month(year, month)
        if day < 1 or day > max_day:
            raise CalendarSpecError(
                f"day {day} is out of range for {self.calendar_id} month {month}"
            )


def gregorian_ce_spec() -> CalendarSpec:
    """The hardcoded Gregorian CE calendar used by the current campaign."""
    names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return CalendarSpec(
        calendar_id=GREGORIAN_CE,
        era_label="CE",
        months=tuple(
            MonthSpec(index=index, name=name, days=days)
            for index, (name, days) in enumerate(zip(names, lengths, strict=True), start=1)
        ),
        leap_rule="standard",
        spec_version="gregorian/1",
    )


#: The active calendar spec for v1. A future version selects this per campaign.
CALENDAR: CalendarSpec = gregorian_ce_spec()


def resolve_relative_year(negative_offset: int, *, anchor_year: int = CURRENT_CAMPAIGN_YEAR) -> int:
    """Resolve a legacy ``-N`` relative year once against an explicit in-game anchor.

    ``-220`` against an anchor of ``505`` yields ``285``. The result is stable: advancing
    the campaign year never recalculates an already-stored value.
    """
    if negative_offset >= 0:
        raise CalendarSpecError("relative-year shorthand requires a negative offset")
    return anchor_year + negative_offset


class CampaignDate(BaseModel):
    """A partial or exact in-game date as integer components under one calendar.

    All components are optional so undated, year-only, or year/month records remain
    valid without placeholders. A BCE year is a negative integer.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    calendar_id: str = GREGORIAN_CE
    year: int | None = None
    month: int | None = Field(default=None, ge=1, le=12)
    day: int | None = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def validate_components(self) -> CampaignDate:
        if self.day is not None and self.month is None:
            raise CalendarSpecError("a campaign date with a day requires a month")
        if self.calendar_id != GREGORIAN_CE:
            raise CalendarSpecError(f"unsupported calendar_id: {self.calendar_id}")
        if self.year is not None and self.month is not None and self.day is not None:
            CALENDAR._require_valid(self.year, self.month, self.day)
        return self

    def is_complete(self) -> bool:
        return self.year is not None and self.month is not None and self.day is not None

    def day_ordinal(self) -> int | None:
        if self.year is None:
            return None
        return CALENDAR.day_ordinal(self.year, self.month, self.day)


def compare_same_calendar(a: CampaignDate, b: CampaignDate) -> int:
    """Order two campaign dates within the same calendar.

    Raises ``CalendarSpecError`` if the dates carry different calendars. Partial dates
    compare by their available components (year, then month, then day). Returns negative,
    zero, or positive like ``cmp``.
    """
    if a.calendar_id != b.calendar_id:
        raise CalendarSpecError(
            "campaign dates under different calendars cannot be directly ordered"
        )
    for left, right in (a.year, b.year), (a.month, b.month), (a.day, b.day):
        if left == right:
            continue
        if left is None:
            return -1
        if right is None:
            return 1
        return -1 if left < right else 1
    return 0


class DateRole(StrEnum):
    """Which temporal concept a campaign date fills on a claim or relationship."""

    EFFECTIVE_FROM = "effective_from"
    EFFECTIVE_UNTIL = "effective_until"
    EXPECTED = "expected"
    OBSERVED = "observed"
