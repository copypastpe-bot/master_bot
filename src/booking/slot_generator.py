"""Pure slot generator for self-booking.

Given a master's available windows for a single date and the list of already-
taken bookings on that date, return the list of start times (HH:MM) where a
new booking of the requested duration would fit without overlap.

This module is intentionally pure: no DB, no aiosqlite, no network. The caller
loads inputs (weekly schedule rows, the date exception if any, active orders)
and passes them in as plain values. This keeps the algorithm fully testable
without fixtures and gives one place to evolve the rules — every flow (public
page, client bot, admin Mini App) funnels through here.

Rules:
- Slot candidates are produced at 30-minute steps (`SLOT_STEP_MINUTES`)
  starting from the window's start; a candidate that would end past the
  window's end is dropped.
- "Overlap" uses the standard interval intersection rule:
  existing.start < cand.end AND existing.end > cand.start.
  Adjacent intervals (existing.end == cand.start, or vice versa) do NOT count
  as overlap — back-to-back bookings are allowed.
- A date-level exception with kind='off' returns no slots regardless of weekly.
- A date-level exception with kind='override' replaces the weekly intervals
  for that date with the single override interval.
- If `now` is provided and `target_date` is the same calendar date as `now`,
  any candidate whose start is at or before `now` is pruned (you can't book
  a slot that has already started).
"""
from datetime import date as date_cls, datetime, time, timedelta
from typing import Optional


SLOT_STEP_MINUTES = 30


def _to_dt(target_date: str, hhmm: str) -> datetime:
    """Combine 'YYYY-MM-DD' + 'HH:MM' into a naive datetime."""
    d = date_cls.fromisoformat(target_date)
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(d, time(h, m))


def _fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def generate_slots(
    *,
    weekly_intervals: list[tuple[str, str]],
    exception: Optional[dict],
    duration_minutes: int,
    existing_bookings: list[tuple[str, int]],
    now: Optional[datetime],
    target_date: str,
) -> list[str]:
    """Return available start times for `target_date` ordered ascending.

    Args:
        weekly_intervals: list of (start_HHMM, end_HHMM) windows from
            master_schedule_weekly, filtered to the target weekday.
        exception: matching row from master_schedule_exceptions for the date,
            or None. Shape: {"kind": "off" | "override",
                             "start": "HH:MM" | None, "end": "HH:MM" | None}.
        duration_minutes: length of the service to book.
        existing_bookings: list of (start_HHMM, duration_minutes) of orders
            already taking time on this date that should block overlap.
        now: current wall clock used only to prune today's past slots; None
            disables pruning (useful in tests).
        target_date: ISO 'YYYY-MM-DD'.
    """
    # Apply date-level exception first.
    if exception is not None:
        if exception["kind"] == "off":
            return []
        if exception["kind"] == "override":
            intervals = [(exception["start"], exception["end"])]
        else:
            # Unknown kind — fall back to weekly to fail-open rather than -closed.
            intervals = weekly_intervals
    else:
        intervals = weekly_intervals

    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=SLOT_STEP_MINUTES)

    # Precompute existing intervals as concrete datetime ranges.
    existing_ranges = [
        (_to_dt(target_date, s), _to_dt(target_date, s) + timedelta(minutes=d))
        for s, d in existing_bookings
    ]

    # Pruning predicate for "today" — only meaningful when `now` is set and
    # the calendar date matches.
    prune_past = (
        now is not None
        and date_cls.fromisoformat(target_date) == now.date()
    )

    results: list[str] = []
    for win_start, win_end in intervals:
        cursor = _to_dt(target_date, win_start)
        end_dt = _to_dt(target_date, win_end)

        while cursor + duration <= end_dt:
            cand_end = cursor + duration

            if prune_past and cursor <= now:  # type: ignore[operator]
                cursor += step
                continue

            overlap = any(
                e_start < cand_end and e_end > cursor
                for e_start, e_end in existing_ranges
            )
            if not overlap:
                results.append(_fmt(cursor))

            cursor += step

    return results
