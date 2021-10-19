"""Functions to parse a schedule string. In its most basic form, a schedule
will just be a Cron string. However, it may also be one of:
    # If no day or from due date/completed date is specified, we will default to
    # "from completed date"
    - Every (X) days/weeks/months/years, (at 9am)
    - Every (X) days/weeks/months/years, (from due date/completed date), (at 9am)
    - Every (X) weeks, on (monday/tuesday/wednesday/...), (at 9am)
    - Every (X) months, on the last day, (at 9am)
    - Every (X) months/years, on day (X), (at 9am)

    - Every (day/weekday), (at 9am)
    - Every (Mon/Tue/Weds...), (at 9am)
    - Every (Jan/Feb/March...) on the (X) day
    
To implement:
    - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
    - Every (X) months on the (first/last) workday
    - Every (Jan/Feb/March...) on the (X) day
"""


import calendar
from croniter import croniter
from enum import Enum
from datetime import date, datetime, time, timedelta, tzinfo
from dateutil import parser
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal
import re
from typing import List, Optional, Tuple, Union

from notion import Task, now_utc


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


WEEKDAYS = {
    **{d.lower(): i for i, d in enumerate(calendar.day_name, start=0)},
    **{d.lower(): i for i, d in enumerate(calendar.day_abbr, start=0)},
}

MONTHS = {
    **{m.lower(): i for i, m in enumerate(calendar.month_name, start=0)},
    **{m.lower(): i for i, m in enumerate(calendar.month_abbr, start=0)},
}


class Schedule:
    # The interval (can be one of "days", "weeks", "months", "years")
    interval: Interval

    # The frequency (e.g. "1", "2", etc. - how many intervals elapse between events)
    frequency: int

    # The base to begin from
    base: datetime

    # Time that it's due
    at_time: time

    # Specific days of the week/month/year, as numbers (last is represented as -1)
    days: Optional[List[int]]

    def __init__(self, task: Task):
        """Parse the schedule string and initialize with appropriate values."""
        # If there is no schedule, we can't handle this
        if task.schedule is None:
            raise Exception(f"Task '{task.name}' has no schedule.")

        # Handle some special cases...
        schedule = handle_special_cases(task.schedule)

        # Handle the simple case of "Every (X) (interval)". Components are separated by
        # commas to make processing easier. Then, each piece is separated by a space.
        components = [s.strip() for s in schedule.split(",")]

        # We should always have a frequency and interval component, e.g.
        # "Every (frequency) (interval)"
        interval, frequency = parse_frequency_and_interval(components[0])
        self.interval = interval
        self.frequency = frequency

        # If there is more to parse, we expect to have _either_ a specification of starting
        # from due date/completed date, _or_ specific days this should be on, and maybe
        # a desired time it's due.
        start_from: Optional[StartFrom] = None

        # Default time due is at the end of the day (midnight).
        today_at_desired_time = parser.parse("12am").replace(tzinfo=tzlocal())
        for c in components[1:]:
            # Check if it's of the form "from due date/start"
            if c.startswith("from"):
                start_from = parse_start_from(c)
            elif c.startswith("on"):
                # Parse this as a specific set of days.
                if self.interval == Interval.DAYS:
                    # "Every 3 days, on Tuesday" doesn't make sense
                    raise Exception(
                        f"Cannot process task '{task.name}' - schedules with intervals of 'days' cannot execute on specific days"
                    )
                elif self.interval == Interval.WEEKS:
                    # Parse weekdays is a bit more general; it handles parsing day strings as well
                    # TODO(fwallace): Could I pass a dictionary of replacements here, make this more general?
                    self.days = parse_weekdays(c)
                else:
                    # Otherwise, we expect this to be a set of numeric days of the week/month/year
                    self.days = parse_days(c)
            elif c.startswith("at"):
                today_at_desired_time = parser.parse(c[3:]).replace(
                    tzinfo=tzlocal()
                )

        # Now, check some of our configuration and make sure the base is set appropriately.
        # We set the base depending on `start_from`.
        if self.days and start_from:
            raise Exception(
                f"Can't set both 'days' and whether to start from due date/completed date."
            )

        self.base = get_base(task, start_from, self.days)

        self.at_time = time(
            hour=today_at_desired_time.hour,
            minute=today_at_desired_time.minute,
            tzinfo=today_at_desired_time.tzinfo,
        )


def get_next(
    base: datetime,
    interval: Interval,
    frequency: int,
    at_time: time,
    days: Optional[list[int]] = None,
) -> datetime:
    """Get the next due date, starting from the given base."""

    # TODO(fwallace): I have to make sure the base is in our local timezone, as well.
    # If it's UTC, this might all get a bit mucked up (I could complete something that's
    # supposed to be daily after midnight UTC, and it will skip a day)
    # TODO(fwallace): When I'm formatting the due date, I should remove the time
    # component if it's all zeroes.
    # TODO(fwallace): How do we deal with the desired time (e.g. if I have a task every
    # day at 9am, and I completed it today at 1am, how do I ensure it is recreated for
    # 9am today?) Do I replace hour + minute, and check if the base is < that (e.g. )
    next_due_date = base
    now = datetime.now(tzlocal())

    # How many days, weeks, months, years have elapsed since the base?
    # Days, months, and years are pretty simple
    years_elapsed = now.year - base.year
    months_elapsed = (years_elapsed * 12) + (now.month - base.month)
    days_elapsed = (now - base).days

    # Weeks are a little more complex, because we want "week boundaries crossed" (e.g.
    # Sunday -> Monday is 1 week elapsed, but only one day). To do that, we compare
    # Monday of the week we're in, to Monday of the week the base is in, and divide
    # by the number of days in a week. We use the floor operator (`//`).
    weeks_elapsed = (
        (now - relativedelta(days=now.weekday()))
        - (base - relativedelta(days=base.weekday()))
    ).days // 7

    # Calculate elapsed times and how many days/weeks/months/years we would add, based
    # on frequency, for all possible intervals. This is very cheap, and means we can
    # handle cases generically below. To figure out how many (X) to add, we figure out
    # how many periods we've missed (divide by frequency), and add one.
    elapsed_times = {
        "days": days_elapsed,
        "weeks": weeks_elapsed,
        "months": months_elapsed,
        "years": years_elapsed,
    }
    to_add = {
        k: ((v // frequency) + 1) * frequency for k, v in elapsed_times.items()
    }

    if not days:
        next_due_date = next_due_date + relativedelta(
            **{interval.name.lower(): to_add[interval.name.lower()]}
        )
    else:
        # Otherwise, we have specific days that this is supposed to execute
        # on.
        #
        # If today is an option, figure out if we've already passed the
        # due time. If not, create it for today.
        due_today_local = now.replace(
            hour=at_time.hour, minute=at_time.minute, second=0
        )
        today_tuple = due_today_local.timetuple()
        if interval == Interval.WEEKS:
            # For each day, check if that due date is greater than our base
            weekday = today_tuple.tm_wday
            # The _latest_ this will be due is (frequency) weeks from `base`, at the
            # desired time.
            latest_due = base + relativedelta(
                weeks=to_add[interval.name.lower()]
            )

            print(
                f"base: {base}, latest: {latest_due}, weekday: {weekday}, due today local: {due_today_local}"
            )

            for d in days:
                if d < weekday:
                    # If the desired day is less than the current weekday, go to the next
                    # week we're interested in. For example, if the day we're interested
                    # in is Tuesday (1), and it's currently Thursday (3), we need to add
                    # 5 days: (7 + 1) - 3
                    delta = relativedelta(
                        days=(
                            (7 * to_add[interval.name.lower()]) + d - weekday
                        )
                    )
                    print(f"d > weekday")
                elif d == weekday:
                    # If it's today, we may or may not have passed the due time already.
                    # If we haven't, set latest due to today at that time. Otherwise, go
                    # to next week again.
                    print(f"d = weekday")
                    if due_today_local > now:
                        # latest_due = due_today_local
                        # break
                        print("Still have time today?")
                        delta = relativedelta(
                            days=(7 * (to_add[interval.name.lower()] - 1))
                        )
                    else:
                        print(
                            f"to add: {to_add[interval.name.lower()]}, d: {d}, weekday: {weekday}"
                        )
                        delta = relativedelta(
                            days=(
                                (7 * to_add[interval.name.lower()])
                                + d
                                - weekday
                            )
                        )
                else:
                    # This day has yet to pass this week. Calculate the delta.
                    delta = relativedelta(
                        days=(7 * (to_add[interval.name.lower()] - 1))
                        + (d - weekday)
                    )

                # If the next due date, on the specified day, is less than the current
                # next due date, use that.
                next_due_on_day = due_today_local + delta
                print(
                    f"day: {d}, delta: {delta}, next due: {next_due_on_day}, latest due: {latest_due}"
                )
                if next_due_on_day < latest_due:
                    latest_due = next_due_on_day

            next_due_date = latest_due
        elif interval == Interval.MONTHS:
            pass
        elif interval == Interval.YEARS:
            pass
        else:
            # We shouldn't be able to get here, but let's be extra safe.
            raise Exception(
                f"Can't get next due date with days {days}, base {base}, and interval {interval.name} - unknown interval"
            )

        #
        # If we have a time component, it's possible that the next due
        # date is today at that time.
    # This is probably already done, but just be safe here.
    return next_due_date.replace(
        hour=at_time.hour, minute=at_time.minute, second=0, microsecond=0
    )

    # If we have a time component, it's possible that the next due date is
    # today at that time. Construct that time and compare to our base.
    #
    # If the base is already past that time, get the delta (days, weeks,
    # months, or years), add it on to the given base, and return the datetime.

    # Otherwise, we have specific days (and maybe times) that we're interested
    # in.
    #
    # If it's on a weekly interval, and one of the days we want to execute on
    # is today, repeat as above (construct datetime, compare to base). If there
    # are no more days we're interested in this week (no days > current day),
    # increment by one week, set the day to the first day in `self.days`, and
    # time to desired time.
    #
    # If it's on a monthly interval, perform the same procedure (but looking
    # until the end of the month).
    #
    # If it's on a yearly interval, again do the same.

    # If we have a time component, make sure it's set on the object. Otherwise, zero
    # everything out.

    return


def get_base(
    task: Task,
    start_from: Optional[StartFrom] = None,
    days: Optional[List[int]] = None,
) -> datetime:
    """Get the base, given a task and an optional specification of when to start
    from."""
    # Figure out what the base time we want is. If we have "start from", it'll tell us
    # to use one of the due date, or completed date. For now, `last_edited_time` will
    # have to approximate completed date.
    #
    # If we don't have "start from", the base will depend on if specific days have been
    # asked for.
    if start_from == StartFrom.COMPLETED_DATE:
        base = task.last_edited_time
    elif start_from == StartFrom.DUE_DATE:
        base = task.due_date
    else:
        if days is None:
            # If no specific days are specified, that means this looks like, for example,
            # "Every 1 weeks". We default to using the completed time, unless told
            # otherwise.
            start_from = StartFrom.COMPLETED_DATE
            base = task.last_edited_time
        else:
            # Otherwise, we have specific days this is supposed to execute on. Use
            # the due date as the base (e.g. "Every 2 weeks, on Thursday" should
            # start from its due date.)
            start_from = StartFrom.DUE_DATE
            base = task.due_date

    if base is None:
        raise Exception(
            f"Cannot determine base for task '{task.name}' starting from {start_from.name}."
        )

    return base


def handle_special_cases(to_parse: str) -> str:
    """Handle special case strings. We just convert them to known format
    so our generic parsers can handle them:
        - Every (day/weekday) (at 9am)
        - Every (Mon/Tue/Weds...) (at 9am)"""
    s = to_parse.lower()
    if s.startswith("every day"):
        return s.replace("every day", "Every 1 weeks, on 0-6")
    elif s.startswith("every weekday"):
        return s.replace("every weekday", "Every 1 weeks, on 0-4")
    elif any([s.startswith(f"every {k}") for k in WEEKDAYS]):
        # Otherwise, if it's every Mon/Tue/Weds, handle that...
        parts = s.split(",")
        return s.replace(parts[0], f"Every 1 weeks, on {parts[0][6:]}")

    return to_parse


def parse_frequency_and_interval(to_parse: str) -> Tuple[Interval, int]:
    """Parse a string with frequency and interval."""
    parts = to_parse.split(" ")
    try:
        # We can ignore the "Every" - skip straight to frequency
        frequency = int(parts[1])

        # Then, parse the interval as an enum
        interval = Interval[parts[2].upper()]

        return interval, frequency
    except KeyError:
        raise Exception(f"No known interval {parts[2]}")
    except Exception as e:
        raise Exception(
            f"Failed to parse frequency and interval string '{to_parse}', error: {e}"
        )


def parse_start_from(to_parse: str) -> StartFrom:
    """Parse a string with "from due date/completed date"."""
    # Strip the "from", replace the space with an underscore,
    # and uppercase. Then, return the associated enum.
    try:
        ret = StartFrom[to_parse[5:].replace(" ", "_").upper()]
        return ret
    except KeyError:
        raise Exception(f"No known start from {to_parse[5:]}")
    except Exception as e:
        raise Exception(
            f"Failed to parse start from string '{to_parse}', error: {e}"
        )


def parse_weekdays(to_parse: str) -> List[int]:
    """In addition to parsing days numerically, we also parse weekday strings:
    - on (monday/tuesday/...)
    - on (mon/tue/...)"""
    try:
        # If the string to parse starts with "on", strip that out.
        to_parse = to_parse.replace("on ", "")

        numeric_values = parse_days(to_parse)

        # If we got some values from `parse_days`, then we can assume they
        # didn't specify weekdays as strings
        if len(numeric_values) > 0:
            return check_numerics(numeric_values, 0, 6)

        # Otherwise, parse weekdays. We'll do this by turning them into a
        # numeric format compatible with `parse_days()` (replacing all weekday
        # strings with numbers)
        #
        # There is some subtle but _VERY IMPORTANT_ behavior here. Most day abbreviations are
        # subsets of the full day (e.g. "tue", "tuesday"). We sort the list of day names by
        # length in reverse order to make sure that full day names are _matched first_. If we
        # don't do this, a string like "monday/tuesday" may be turned into "0day/1day".
        pattern = "|".join(
            sorted(
                (re.escape(k) for k in WEEKDAYS),
                key=lambda s: len(s),
                reverse=True,
            )
        )
        to_parse = re.sub(
            pattern,
            # We have to cast to a string to make re.sub happy (it expects a function
            # that returns a string here)
            lambda m: str(WEEKDAYS[m.group(0).lower()]),
            to_parse,
            flags=re.IGNORECASE,
        )

        return check_numerics(parse_numerics(to_parse), 0, 6)
    except Exception as e:
        raise Exception(
            f"Failed to parse weekdays string '{to_parse}', error: {e}"
        )


def check_numerics(numerics: List[int], min: int, max: int) -> List[int]:
    """Check that everything in the list is in bounds"""
    s = sorted(numerics)

    if s[0] < min or s[-1] > max:
        raise Exception(
            f"Out of bounds numbers in list {numerics}, min: {min}, max: {max}"
        )

    return s


def parse_days(to_parse: str) -> List[int]:
    """Takes a string detailing specific days the schedule should execute
    on. Can be one of the following:
    - on day (X)
    - on day (1-n/n+1-z/X)
    - on the last day"""
    try:
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
    except Exception as e:
        raise Exception(
            f"Failed to parse days string '{to_parse}', error: {e}"
        )


def parse_numerics(to_parse: str) -> List[int]:
    """Parse a string containing numeric values and return a list of integers."""
    try:
        # Split the string, and filter into ranges and values
        parts = to_parse.split("/")
        ranges = list(filter(lambda s: "-" in s, parts))

        # Immediately add any hardcoded numbers
        numeric_values = [
            int(v) for v in filter(lambda s: "-" not in s, parts)
        ]

        # Parse ranges and add them as well
        for r in ranges:
            i, n = [int(s) for s in r.split("-")]
            numeric_values.extend(range(i, n + 1))

        return sorted(numeric_values)
    except Exception as e:
        raise Exception(
            f"Failed to parse numeric literal string: '{to_parse}', error: {e}"
        )


def process_schedule_str(schedule: str) -> datetime:
    """Process a schedule string, split into its components, and return the next
    due date."""
    now = now_utc()
    return now_utc()


def get_next_due_date(task: Task) -> datetime:
    """Given a task, figure out what its next due date will be based on its schedule."""
    base = now_utc()
    if task.schedule is None:
        raise Exception(f"Task '{task.name}' has no schedule")

    # Check if it's an expression that croniter can handle, or if we need to process
    # ourselves.
    if croniter.is_valid(task.schedule):
        # croniter's got this
        iter = croniter(task.schedule, base)
        return iter.get_next(datetime)


# TODO(fwallace): Confirm that this will confirm a due date _in local time_
# TODO(fwallace): Confirm that this will set the due date in notion _in local time_
