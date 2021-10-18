"""Test the schedule utility."""

import pytest
import re

from utils.schedule import (
    Interval,
    StartFrom,
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
    assert parse_weekdays("on mon/tuesday") == [0, 1]
    assert parse_weekdays("on MON-TUE/FRI-SAT") == [0, 1, 4, 5]

    # Check that it throws an exception if we're asking for out of bounds days
    with pytest.raises(
        Exception,
        match=re.escape(
            r"Failed to parse weekdays string 'day 7', error: Out of bounds numbers in list [7], min: 0, max: 6"
        ),
    ):
        parse_weekdays("on day 7")


def test_handle_special_cases():
    """Unit test `handle_special_cases`."""
    assert handle_special_cases("Every day") == "Every 1 weeks, on 0-6"
    assert (
        handle_special_cases("Every day, at 9am")
        == "Every 1 weeks, on 0-6, at 9am"
    )
    assert handle_special_cases("Every weekday") == "Every 1 weeks, on 0-4"
    assert (
        handle_special_cases("Every weekday, at 9am")
        == "Every 1 weeks, on 0-4, at 9am"
    )
    assert (
        handle_special_cases("Every saturday/sun")
        == "Every 1 weeks, on saturday/sun"
    )
    assert (
        handle_special_cases("Every saturday/sun, at 9am")
        == "Every 1 weeks, on saturday/sun, at 9am"
    )

    assert handle_special_cases("Every 1 weeks") == "Every 1 weeks"


#   - Every (X) days (from due date/now)
#   - Every (day/weekday)
#   - Every (Mon/Tues/Weds...)
#   - Every (X) weeks on (monday/tuesday/wednesday/...)
#   - Every (X) months on the (X) day
#   - Every (X) months on the (first/last) day
#   - Every (X) months (from due date/now)
#   - Every (Jan/Feb/March...) on the (X) day
#   - Every (X) years
#   - Every (X) years on the (X) day
#   - Every (X) years (from due date/now)

# There's also a time component (e.g. "at 9am")

#   - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
#   - Every (X) months on the (first/last) workday
