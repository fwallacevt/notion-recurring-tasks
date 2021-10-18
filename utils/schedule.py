"""Functions to parse a schedule string. In its most basic form, a schedule
will just be a Cron string. However, it may also be one of:
  - Every (X) days (from due date/now)
  - Every (day/weekday)
  - Every (Mon/Tues/Weds...)
  - Every (X) weeks on (monday/tuesday/wednesday/...)
  - Every (X) months on the (X) day
  - Every (X) months on the (first/last) day
  - Every (X) months (from due date/now)
  - Every (Jan/Feb/March...) on the (X) day
  - Every (X) years 
  - Every (X) years on the (X) day
  - Every (X) years (from due date/now)

There's also a time component (e.g. "at 9am")

  - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
  - Every (X) months on the (first/last) workday
"""

# These have components of:
# - interval (daily/weekly/monthly/yearly)
# - frequency (every (X) interval)
# - Specific value(s) ()

import calendar
from datetime import datetime
from enum import Enum
import re
from typing import List, Optional, Tuple
from croniter import croniter

from notion import now_utc, Task

# Can I break these strings down into their components? They have an:
#   - Interval
#   - Frequency
#   - Specific value (day or number of days?)
#   - When to start from (due date/now)


class StartFrom(Enum):
    """Enum for possible values for when to start the schedule."""

    DUE_DATE = 1
    COMPLETED_DATE = 2


class Interval(Enum):
    """Enum for possible interval values."""

    DAYS = 1
    WEEKS = 2
    MONTHS = 3
    YEARS = 4


class Schedule:
    # The interval (can be one of "days", "weeks", "months", "years")
    interval: Interval

    # The frequency (e.g. "1", "2", etc. - how many intervals elapse between events)
    frequency: int

    # Specific months, if specified. For example, "Jan" or "January"
    months: Optional[List[str]]

    # Specific days of the week/month/year, as numbers (last is represented as -1)
    days: Optional[List[int]]

    # When to start from, either the due date or completed date
    start_from: Optional[StartFrom]

    def __init__(self, schedule: str):
        """Parse the schedule string and initialize with appropriate values."""
        # Handle the simple case of "Every (X) (interval)". Components are separated by
        # commas to make processing easier. Then, each piece is separated by a space.
        components = [s.strip() for s in schedule.split(",")]

        # We should always have a frequency and interval component, e.g.
        # "Every (frequency) (interval)"
        interval, frequency = parse_frequency_and_interval(components[0])
        self.interval = interval
        self.frequency = frequency

        # If there is more to parse, we expect to have _either_ a specification of starting
        # from due date/completed date, _or_ specific days this should be on
        if len(components) > 1:
            # Check if it's of the form "from due date/start"
            s = components[1]
            if s.startswith("from"):
                self.start_from = parse_start_from(components[1])
            else:
                # Parse this as a specific set of days.
                if self.interval == Interval.DAYS:
                    # "Every 3 days on Tuesday" doesn't make sense
                    raise Exception(
                        f"Schedules with intervals of 'days' cannot execute on specific days"
                    )
                elif self.interval == Interval.WEEKS:
                    # Parse weekdays is a bit more general; it handles parsing day strings as well
                    # TODO(fwallace): Could I pass a dictionary of replacements here, make this more general?
                    self.days = parse_weekdays(s)
                else:
                    # Otherwise, we expect this to be a set of numeric days of the week/month/year
                    self.days = parse_days(s)

        # TODO(fwallace): Finally, handle time (e.g. at 9am)


def parse_frequency_and_interval(to_parse: str) -> Tuple[Interval, int]:
    """Parse a string with frequency and interval."""
    parts = to_parse.split(" ")

    # We can ignore the "Every" - skip straight to frequency
    frequency = int(parts[1])

    # Then, parse the interval as an enum
    interval = Interval[parts[2].upper()]

    return interval, frequency


def parse_start_from(to_parse: str) -> StartFrom:
    """Parse a string with "from due date/completed date"."""
    # Strip the "from", replace the space with an underscore,
    # and uppercase. Then, return the associated enum.
    return StartFrom[to_parse[5:].replace(" ", "_").upper()]


WEEKDAYS = {
    **{d.lower(): i for i, d in enumerate(calendar.day_name)},
    **{d.lower(): i for i, d in enumerate(calendar.day_abbr)},
}


def parse_weekdays(to_parse: str) -> List[int]:
    """In addition to parsing days numerically, we also parse weekday strings:
    - on (monday/tuesday/...)
    - on (mon/tues/...)"""
    # If the string to parse starts with "on", strip that out.
    to_parse = to_parse.replace("on ", "")

    numeric_values = parse_days(to_parse)

    # If we got some values from `parse_days`, then we can assume they
    # didn't specify weekdays as strings
    if len(numeric_values) > 0:
        return numeric_values

    # Otherwise, parse weekdays. We'll do this by turning them into a
    # numeric format compatible with `parse_days()` (replacing all weekday
    # strings with numbers)
    pattern = "|".join(sorted(re.escape(k) for k in WEEKDAYS))
    to_parse = re.sub(
        pattern,
        # We have to cast to a string to make re.sub happy (it expects a function
        # that returns a string here)
        lambda m: str(WEEKDAYS[m.group(0).lower()]),
        to_parse,
        flags=re.IGNORECASE,
    )

    return parse_numerics(to_parse)


def parse_days(to_parse: str) -> List[int]:
    """Takes a string detailing specific days the schedule should execute
    on. Can be one of the following:
    - on day (X)
    - on day (1-n/n+1-z/X)
    - on the last day"""
    # If the string to parse starts with "on", strip that out.
    to_parse = to_parse.replace("on ", "")

    # If is "on the last day", just return [-1]
    if to_parse == "the last day":
        return [-1]

    # Otherwise, we'll build a list of numeric values
    numeric_values: List[int] = []

    # Otherwise, if our string starts with "on day", we'll assume it's specifying numeric values
    if to_parse.startswith("day"):
        numeric_values = parse_numerics(to_parse[4:])

    return numeric_values


def parse_numerics(to_parse: str) -> List[int]:
    """Parse a string containing numeric values and return a list of integers."""
    # Split the string, and filter into ranges and values
    parts = to_parse[4:].split("/")
    ranges = list(filter(lambda s: "-" in s, parts))

    # Immediately add any hardcoded numbers
    numeric_values = [int(v) for v in filter(lambda s: "-" not in s, parts)]

    # Parse ranges and add them as well
    for r in ranges:
        i, n = [int(s) for s in r.split("-")]
        numeric_values.extend(range(i, n + 1))

    return numeric_values


"""
    - Every (X) days/weeks/months/years (will default to from completed date)

    - Every (X) days/weeks/months/years (from due date/completed date)

    - Every (X) weeks on (monday/tuesday/wednesday/...)
    - Every (X) months on the last day
    - Every (X) months/years on day (X)

    - Every (day/weekday)
    - Every (Mon/Tues/Weds...)
    - Every (Jan/Feb/March...) on the (X) day

There's also a time component (e.g. "at 9am")"""


def process_schedule_str(schedule: str) -> datetime:
    """Process a schedule string, split into its components, and return the next
    due date."""
    now = now_utc()
    return now_utc()


def get_next_due_date(task: Task) -> datetime:
    """Given a task, figure out what its next due date will be based on its schedule."""
    base = now_utc()
    if task.schedule is None:
        raise Exception(f"Task {task.name} has no schedule")

    # Check if it's an expression that croniter can handle, or if we need to process
    # ourselves.
    if croniter.is_valid(task.schedule):
        # croniter's got this
        iter = croniter(task.schedule, base)
        return iter.get_next(datetime)
