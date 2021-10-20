"""Test the schedule utility."""

import re
from datetime import datetime, time

import pytest
from dateutil.relativedelta import relativedelta
from dateutil.tz.tz import tzlocal

from notion.orm import now_utc
from notion.tasks import Task
from utils.schedule import (
    Interval,
    Schedule,
    StartFrom,
    get_next,
    get_next_due_date,
    handle_special_cases,
    parse_days,
    parse_frequency_and_interval,
    parse_numerics,
    parse_start_from,
    parse_weekdays,
)


def test_parse_frequency_and_interval():
    """Unit test for `parse_frequency_and_interval`. This should parse "Every (X) (interval)"."""

    # Test that it works for days, weeks, months, and years, with
    # different interval numbers
    i, f = parse_frequency_and_interval("Every 1 days")
    assert i == Interval.DAYS
    assert f == 1

    i, f = parse_frequency_and_interval("Every 2 weeks")
    assert i == Interval.WEEKS
    assert f == 2

    # Throw in weird capitalization
    i, f = parse_frequency_and_interval("Every 3 MonThs")
    assert i == Interval.MONTHS
    assert f == 3

    i, f = parse_frequency_and_interval("Every 4 YEARS")
    assert i == Interval.YEARS
    assert f == 4

    # Check that it throws an exception if the interval isn't a known one
    with pytest.raises(
        Exception,
        match=r"No known interval GIBBERISH",
    ):
        parse_frequency_and_interval("Every 4 GIBBERISH")


def test_start_from():
    """Unit test for `parse_start_from` This should parse "from due date/completed date"."""
    assert parse_start_from("from due date") == StartFrom.DUE_DATE
    assert parse_start_from("from completed date") == StartFrom.COMPLETED_DATE

    # Check that it throws an exception if it isn't a known one
    with pytest.raises(
        Exception,
        match=r"No known start from GIBBERISH",
    ):
        parse_start_from("from GIBBERISH")


def test_parse_numerics():
    """Unit test for `parse_numerics`."""
    assert parse_numerics("3") == [3]
    assert parse_numerics("3/1-2/7-8") == [1, 2, 3, 7, 8]


def test_parse_days():
    """Unit test for `parse_days`."""
    assert parse_days("on the last day") == [-1]
    assert parse_days("on day 3") == [3]
    assert parse_days("on day 3/1-2/7-8") == [1, 2, 3, 7, 8]


def test_parse_weekdays():
    """Unit test for `parse_days`."""
    assert parse_weekdays("on day 3") == [3]
    assert parse_weekdays("on mon/tuesday") == [1, 2]
    assert parse_weekdays("on MON-TUE/FRI-SAT") == [1, 2, 5, 6]

    # Check that it throws an exception if we're asking for out of bounds days
    with pytest.raises(
        Exception,
        match=re.escape(
            r"Failed to parse weekdays string 'day 8', error: Out of bounds numbers in list [8], min: 1, max: 7"
        ),
    ):
        parse_weekdays("on day 8")


def test_handle_special_cases():
    """Unit test `handle_special_cases`."""
    assert handle_special_cases("Every day") == "Every 1 days"
    assert handle_special_cases("Every day, at 9am") == "Every 1 days, at 9am"
    assert handle_special_cases("Every weekday") == "Every 1 weeks, on 1-5"
    assert (
        handle_special_cases("Every weekday, at 9am") == "Every 1 weeks, on 1-5, at 9am"
    )
    assert (
        handle_special_cases("Every saturday/sun") == "Every 1 weeks, on saturday/sun"
    )
    assert (
        handle_special_cases("Every saturday/sun, at 9am")
        == "Every 1 weeks, on saturday/sun, at 9am"
    )

    assert handle_special_cases("Every 1 weeks") == "Every 1 weeks"


def test_get_next_no_days():
    """Test that we can get the next due date from an interval, frequency, and base."""
    # Check that it works for an event happening every day (starting from today)
    today = (
        datetime.now().astimezone().replace(hour=9, minute=30, second=0, microsecond=0)
    )
    base_time = time(hour=9, minute=30)
    base = datetime.now().astimezone()

    # ----------------- TEST DAYS ----------------- #
    # Test that it works with days
    d = get_next(base, Interval.DAYS, 1, base_time)
    assert d == (today + relativedelta(days=1))

    # We should still get the next future occurrence if our base is farther back in time
    d = get_next(base - relativedelta(weeks=1), Interval.DAYS, 1, base_time)
    assert d == (today + relativedelta(days=1))

    # Test that it works if we adjust the frequency
    d = get_next(base, Interval.DAYS, 2, base_time)
    assert d == (today + relativedelta(days=2))

    # And if our base changes...
    d = get_next(base - relativedelta(days=1), Interval.DAYS, 2, base_time)
    assert d == (today + relativedelta(days=1))

    # ----------------- TEST WEEKS ----------------- #
    # Test that it works with weeks
    d = get_next(base, Interval.WEEKS, 1, base_time)
    assert d == (today + relativedelta(weeks=1))

    # We should still get the next future occurrence if our base is farther back in time
    d = get_next(base - relativedelta(weeks=2), Interval.WEEKS, 1, base_time)
    assert d == (today + relativedelta(weeks=1))

    # Test that it works if we adjust the frequency
    d = get_next(base, Interval.WEEKS, 2, base_time)
    assert d == (today + relativedelta(weeks=2))

    # And if our base changes...
    d = get_next(base - relativedelta(weeks=1), Interval.WEEKS, 2, base_time)
    assert d == (today + relativedelta(weeks=1))

    # ----------------- TEST MONTHS ----------------- #
    # Test that it works with months
    d = get_next(base, Interval.MONTHS, 1, base_time)
    assert d == (today + relativedelta(months=1))

    # We should still get the next future occurrence if our base is farther back in time
    d = get_next(base - relativedelta(months=2), Interval.MONTHS, 1, base_time)
    assert d == (today + relativedelta(months=1))

    # Test that it works if we adjust the frequency
    d = get_next(base, Interval.MONTHS, 2, base_time)
    assert d == (today + relativedelta(months=2))

    # And if our base changes...
    d = get_next(base - relativedelta(months=1), Interval.MONTHS, 2, base_time)
    assert d == (today + relativedelta(months=1))

    # ----------------- TEST YEARS ----------------- #
    # Test that it works with years
    d = get_next(base, Interval.YEARS, 1, base_time)
    assert d == (today + relativedelta(years=1))

    # We should still get the next future occurrence if our base is farther back in time
    d = get_next(base - relativedelta(years=2), Interval.YEARS, 1, base_time)
    assert d == (today + relativedelta(years=1))

    # Test that it works if we adjust the frequency
    d = get_next(base, Interval.YEARS, 2, base_time)
    assert d == (today + relativedelta(years=2))

    # And if our base changes...
    d = get_next(base - relativedelta(years=1), Interval.YEARS, 2, base_time)
    assert d == (today + relativedelta(years=1))


def test_get_next_specific_days():
    """Test that we can get the next due date from an interval, frequency, days, and base."""
    today = (
        datetime.now().astimezone().replace(hour=9, minute=30, second=0, microsecond=0)
    )
    base_time = time(hour=9, minute=30)

    # Start from Monday
    monday = today - relativedelta(days=today.weekday())
    # Internally, we offset everything by 1, so account for that here
    days = [today.weekday(), today.weekday() + 2]

    # ----------------- TEST DAYS ----------------- #
    # Test that it works with days, if there is at least one remaining day this week
    d = get_next(monday, Interval.WEEKS, 1, base_time, days)
    assert d == (today + relativedelta(days=1))

    # Test that it wraps to the next week, if applicable
    d = get_next(today, Interval.WEEKS, 1, base_time, days[:1])
    assert d == (monday + relativedelta(days=7 + days[0] - 1))

    # Test that it returns today, if today is one of the options and desired time hasn't
    # passed yet
    d = get_next(
        today,
        Interval.WEEKS,
        1,
        time(hour=23, minute=59),
        [today.weekday() + 1],
    )
    assert d == today.replace(hour=23, minute=59)

    # Everything should operate the same if we go farther back in time
    d = get_next(monday - relativedelta(weeks=2), Interval.WEEKS, 1, base_time, days)
    assert d == (today + relativedelta(days=1))

    # Test with a different frequency
    d = get_next(monday - relativedelta(weeks=2), Interval.WEEKS, 4, base_time, days)
    assert d == (today - relativedelta(days=1) + relativedelta(weeks=2))

    # ----------------- TEST MONTHS ----------------- #
    # Test that it works with months, if there is at least one remaining day this month
    days = [today.day - 1, today.day + 1]
    d = get_next(today, Interval.MONTHS, 2, base_time, days)
    assert d == (today + relativedelta(days=1))

    # Test that it wraps to the next month, if applicable
    d = get_next(today, Interval.MONTHS, 1, base_time, days[:1])
    assert d == (today + relativedelta(days=-1, months=1))

    # Test that it returns today, if today is one of the options and desired time hasn't
    # passed yet
    d = get_next(
        today,
        Interval.MONTHS,
        1,
        time(hour=23, minute=59),
        [today.day],
    )
    assert d == today.replace(hour=23, minute=59)

    # Everything should operate the same if we go farther back in time
    d = get_next(today - relativedelta(months=2), Interval.MONTHS, 1, base_time, days)
    assert d == (today + relativedelta(days=1))

    # Test with a different frequency
    d = get_next(today - relativedelta(months=2), Interval.MONTHS, 4, base_time, days)
    assert d == (today + relativedelta(days=-1, months=2))

    # ----------------- TEST YEARS ----------------- #
    # Test that it works with years, if there is at least one remaining day this year
    day_of_year = today.timetuple().tm_yday
    days = [day_of_year - 1, day_of_year + 1]
    d = get_next(today, Interval.YEARS, 2, base_time, days)
    assert d == (today + relativedelta(days=1))

    # Test that it wraps to the next year, if applicable
    d = get_next(today, Interval.YEARS, 1, base_time, days[:1])
    assert d == (today + relativedelta(days=-1, years=1))

    # Test that it returns today, if today is one of the options and desired time hasn't
    # passed yet
    d = get_next(
        today,
        Interval.YEARS,
        1,
        time(hour=23, minute=59),
        [day_of_year],
    )
    assert d == today.replace(hour=23, minute=59)

    # Everything should operate the same if we go farther back in time
    d = get_next(today - relativedelta(years=2), Interval.YEARS, 1, base_time, days)
    assert d == (today + relativedelta(days=1))

    # Test with a different frequency
    d = get_next(today - relativedelta(years=2), Interval.YEARS, 4, base_time, days)
    assert d == (today + relativedelta(days=-1, years=2))


def test_schedule_parses_task():
    """Test that the schedule class unpacks our Task object correctly."""
    today = (
        datetime.now().astimezone().replace(hour=7, minute=0, second=0, microsecond=0)
    )

    task = Task(
        date_created=now_utc(),
        last_edited_time=now_utc(),
        name="Test",
        schedule="Every day, at 7am",
        due_date=today - relativedelta(days=3),
    )
    schedule = Schedule(task)
    assert schedule._at_time == time(hour=7, minute=0).replace(tzinfo=tzlocal())
    assert schedule._base == task.last_edited_time
    assert schedule._days == None
    assert schedule._interval == Interval.DAYS
    assert schedule._frequency == 1

    task = Task(
        date_created=now_utc(),
        last_edited_time=now_utc(),
        name="Test",
        schedule="Every day, at 7am, from due date",
        due_date=today - relativedelta(days=3),
    )
    schedule = Schedule(task)
    assert schedule._at_time == time(hour=7, minute=0).replace(tzinfo=tzlocal())
    assert schedule._base == task.due_date
    assert schedule._days == None
    assert schedule._interval == Interval.DAYS
    assert schedule._frequency == 1

    task = Task(
        date_created=now_utc(),
        last_edited_time=now_utc(),
        name="Test",
        schedule="Every 3 weeks, from due date",
        due_date=today - relativedelta(days=3),
    )
    schedule = Schedule(task)
    assert schedule._at_time == time(hour=0, minute=0).replace(tzinfo=tzlocal())
    assert schedule._base == task.due_date
    assert schedule._days == None
    assert schedule._interval == Interval.WEEKS
    assert schedule._frequency == 3

    task = Task(
        date_created=now_utc(),
        last_edited_time=now_utc(),
        name="Test",
        schedule="Every 3 weeks, on mon-wed/friday",
        due_date=today - relativedelta(days=3),
    )
    schedule = Schedule(task)
    assert schedule._at_time == time(hour=0, minute=0).replace(tzinfo=tzlocal())
    assert schedule._base == task.due_date
    assert schedule._days == [1, 2, 3, 5]
    assert schedule._interval == Interval.WEEKS
    assert schedule._frequency == 3

    # Check that it throws an exception if we set specific days and whether to start
    # from due date or completed date
    with pytest.raises(
        Exception,
        match=r"Can't set both 'days' and whether to start from due date/completed date.",
    ):
        task = Task(
            date_created=now_utc(),
            last_edited_time=now_utc(),
            name="Test",
            schedule="Every 3 weeks, on mon-wed/friday, from due date",
            due_date=today - relativedelta(days=3),
        )
        schedule = Schedule(task)

    # Check that we can't ask for specific days if our interval is in days
    with pytest.raises(
        Exception,
        match=r"Cannot process task 'Test' - schedules with intervals of 'days' cannot execute on specific days",
    ):
        task = Task(
            date_created=now_utc(),
            last_edited_time=now_utc(),
            name="Test",
            schedule="Every 3 days, on mon-wed/friday",
            due_date=today - relativedelta(days=3),
        )
        schedule = Schedule(task)
