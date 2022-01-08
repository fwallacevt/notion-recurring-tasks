"""Functions to parse a schedule string."""


import calendar
import re
from datetime import date, datetime, time
from enum import Enum
from typing import List, Optional, Tuple, Union

from croniter import croniter
from dateutil import parser
from dateutil.relativedelta import relativedelta
from loguru import logger

from notion import Task


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
    **{d.lower(): i for i, d in enumerate(calendar.day_name, start=1)},
    **{d.lower(): i for i, d in enumerate(calendar.day_abbr, start=1)},
}

MONTHS = {
    **{m.lower(): i for i, m in enumerate(calendar.month_name, start=1)},
    **{m.lower(): i for i, m in enumerate(calendar.month_abbr, start=1)},
}


class Schedule:
    # The interval (can be one of "days", "weeks", "months", "years")
    _interval: Interval

    # The frequency (e.g. "1", "2", etc. - how many intervals elapse between events)
    _frequency: int

    # The base to begin from
    _base: datetime

    # Time that it's due
    _at_time: Optional[time]

    # Specific days of the week/month/year, as numbers (last is represented as -1)
    _days: Optional[List[int]]

    @property
    def interval(self) -> Interval:
        return self._interval

    @property
    def frequency(self) -> int:
        return self._frequency

    @property
    def base(self) -> datetime:
        return self._base

    @property
    def at_time(self) -> Optional[time]:
        return self._at_time

    @property
    def days(self) -> Optional[List[int]]:
        return self._days

    def __init__(self, task: Task):
        """Parse the schedule string and initialize with appropriate values."""
        logger.info(f"Parsing schedule for task {task.name}, schedule: {task.schedule}")
        # If there is no schedule, we can't handle this
        if task.schedule is None:
            raise Exception(f"Task '{task.name}' has no schedule.")

        # Make sure that days and at_time are initialized
        self._days = None
        self._at_time = None

        # Handle some special cases...
        schedule = handle_special_cases(task.schedule)
        logger.info(
            f"Schedule '{task.schedule}' converted to '{schedule}' after special cases."
        )

        # Handle the simple case of "Every (X) (interval)". Components are separated by
        # commas to make processing easier. Then, each piece is separated by a space.
        components = [s.strip() for s in schedule.split(",")]
        logger.info(f"Schedule has {len(components)} components: {components}.")

        # We should always have a frequency and interval component, e.g.
        # "Every (frequency) (interval)"
        interval, frequency = parse_frequency_and_interval(components[0])
        self._interval = interval
        self._frequency = frequency
        logger.info(
            f"Schedule for task {task.name} has interval {interval.name}, frequency {frequency}."
        )

        # If there is more to parse, we expect to have _either_ a specification of starting
        # from due date/completed date, _or_ specific days this should be on, and maybe
        # a desired time it's due.
        start_from: Optional[StartFrom] = None
        for c in components[1:]:
            # Check if it's of the form "from due date/start"
            if c.startswith("from"):
                start_from = parse_start_from(c)
            elif c.startswith("on"):
                # Parse this as a specific set of days.
                if self._interval == Interval.DAYS:
                    # "Every 3 days, on Tuesday" doesn't make sense
                    raise Exception(
                        f"Cannot process task '{task.name}' - schedules with intervals of 'days' cannot execute on specific days"
                    )
                elif self._interval == Interval.WEEKS:
                    # Parse weekdays is a bit more general; it handles parsing day strings as well
                    self._days = parse_weekdays(c)
                else:
                    # Otherwise, we expect this to be a set of numeric days of the week/month/year
                    self._days = parse_days(c)
            elif c.startswith("at"):
                today_at_desired_time = parser.parse(c[3:])
                self._at_time = time(
                    hour=today_at_desired_time.hour,
                    minute=today_at_desired_time.minute,
                )

        # Now, check some of our configuration and make sure the base is set appropriately.
        # We set the base depending on `start_from`.
        if self._days and start_from:
            raise Exception(
                f"Can't set both 'days' and whether to start from due date/completed date."
            )

        # Get the base, and make sure we sync the timezones on "at_time" and "base"
        self._base = get_base(task, start_from, self._days)
        if self._at_time is not None:
            self._at_time = self._at_time.replace(tzinfo=self._base.tzinfo)

        logger.info(
            f"Schedule for task {task.name} has base {self._base}, at_time {self._at_time}"
        )

    def get_next(self):
        """Get the next due date for this schedule."""
        return get_next(
            self._base,
            self._interval,
            self._frequency,
            self._at_time,
            self._days,
        )


def get_next(
    base: datetime,
    interval: Interval,
    frequency: int,
    at_time: Optional[time] = None,
    days: Optional[list[int]] = None,
) -> Union[datetime, date]:
    """Get the next due date, starting from the given base."""
    logger.info(
        f"Getting next due date with base {base}, interval {interval.name}, frequency {frequency}, at_time {at_time}, and days {days}"
    )

    # If we don't have a time we expect this to be at, simply use all zeroes
    due_time = time()
    if at_time is not None:
        due_time = at_time

    # Standardize on the current timezone, to account for crossing boundaries (e.g. daylight
    # savings time) if we're comparing dates across boundaries. Also, if we don't have "at_time",
    # then we effectively ignore the time component by zeroing it out in `now` as well. Below,
    # we compare the next due date to now, and we only care about the time component if we have
    # a specific time.
    now = datetime.now().astimezone()
    if at_time is None:
        now = now.replace(
            hour=due_time.hour, minute=due_time.minute, second=0, microsecond=0
        )
    base = base.replace(tzinfo=now.tzinfo)
    next_due_date = base.replace(tzinfo=now.tzinfo)

    logger.info(f"Base in local timezone: {next_due_date}")

    # How many days, weeks, months, years have elapsed since the base?
    # Days, months, and years are pretty simple
    years_elapsed = now.year - base.year
    months_elapsed = (years_elapsed * 12) + (now.month - base.month)
    days_elapsed = (now - base).days

    # Weeks are a little more complex, because we want "week boundaries crossed" (e.g.
    # Sunday -> Monday is 1 week elapsed, but only one day). To do that, we compare
    # Monday of the week we're in, to Monday of the week the base is in, and divide
    # by the number of days in a week. We use the floor operator (`//`). We also make
    # sure to zero out the time component when comparing, to get an accurate picture
    # of days elapsed.
    weeks_elapsed = (
        (now - relativedelta(days=now.weekday()))
        - (
            base.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            - relativedelta(days=base.weekday())
        )
    ).days // 7

    # Calculate elapsed times and how many days/weeks/months/years we would add, based
    # on frequency, for all possible intervals. This is very cheap, and means we can
    # handle cases generically below. To figure out how many (X) to add, we figure out
    # how many periods we've missed (divide by frequency).
    elapsed_times = {
        "days": days_elapsed,
        "weeks": weeks_elapsed,
        "months": months_elapsed,
        "years": years_elapsed,
    }
    to_add = {k: max((v // frequency) * frequency, 0) for k, v in elapsed_times.items()}

    logger.info(f"Elapsed time since base: {elapsed_times}")
    logger.info(f"Times to add: {to_add}")

    if not days:
        logger.info(f"No days - adding intervals.")
        next_due_date = next_due_date + relativedelta(
            **{
                interval.name.lower(): to_add[interval.name.lower()] + frequency
            }  # type: ignore
        )
    else:
        # Otherwise, we have specific days that this is supposed to execute
        # on.
        logger.info(f"Have specific days {days} this should execute on.")

        # If we have particular days, first figure out when the _latest_ it
        # will be due is. This is the base + intervals to add + frequency + offset
        latest_due = base + relativedelta(
            **{
                interval.name.lower(): to_add[interval.name.lower()] + frequency
            }  # type: ignore
        )

        # Also factor in the first day this may execute on. Offset is the first day - 1
        # if that's non negative, or the last day of the month. For example, if days is
        # [5, 10], interval is monthly, and frequency is 1, we don't want to say the latest
        # this could be due is next month on the first, because that's not correct. The
        # correct latest due date would be _*next month on the 5th*_. That is what we're
        # accounting for here.
        offset = (
            days[0] - 1
            if days[0] != -1
            else calendar.monthrange(latest_due.year, latest_due.month)[-1]
        )
        latest_due = latest_due + relativedelta(days=offset)
        logger.info(
            f"With base {base}, delta {interval.name.lower()}: {to_add[interval.name.lower()] + frequency}, offset {offset}, the latest possible due date is: {latest_due}"
        )

        if interval == Interval.WEEKS:
            # Next, figure out which week we're comparing against. This is Monday of either
            # this week, or the last week this schedule would have executed.
            due_base_local = (
                base.replace(hour=due_time.hour, minute=due_time.minute, second=0)
                - relativedelta(days=base.weekday())
                + relativedelta(weeks=to_add[interval.name.lower()])
            )
        elif interval == Interval.MONTHS:
            # Figure out which month we're comparing against. This is the first day
            # of this month, or the last month this schedule may have executed in.
            due_base_local = base.replace(
                hour=due_time.hour, minute=due_time.minute, second=0, day=1
            ) + relativedelta(
                **{interval.name.lower(): to_add[interval.name.lower()]}  # type: ignore
            )
        elif interval == Interval.YEARS:
            # Figure out which year we're comparing against. This is the first day
            # of this year, or the last year this schedule may have executed in.
            due_base_local = base.replace(
                hour=due_time.hour,
                minute=due_time.minute,
                second=0,
                day=1,
                month=1,
            ) + relativedelta(
                **{interval.name.lower(): to_add[interval.name.lower()]}  # type: ignore
            )
        else:
            # We shouldn't be able to get here, but let's be extra safe.
            raise Exception(
                f"Can't get next due date with days {days}, base {base}, and interval {interval.name} - unknown interval"
            )
        logger.info(f"Due base local with interval {interval.name}: {due_base_local}")

        # Now that we have a base to work from, we can figure out when this would next
        # be due on one of the days we're interested in.
        for d in days:
            # Then, for each of the days we're interested in, figure out when it would
            # be due next, on that day (either this interval, or `frequency` intervals
            # in the future)
            if d == -1:
                # If we're looking for the last day of the month, find the last day and
                # replace `due_base_local.day`
                next_due_on_day = due_base_local.replace(
                    day=calendar.monthrange(due_base_local.year, due_base_local.month)[
                        -1
                    ]
                )
            else:
                # We always subtract one because "day n" is an offset of n-1, etc. (since
                # we're starting on day 1)
                next_due_on_day = due_base_local + relativedelta(days=d - 1)

            logger.info(f"Next due on day {d}: {next_due_on_day}. Now: {now}")
            if next_due_on_day < now:
                if d == -1:
                    # If we're looking for the last day of the month, set that for the
                    # next month. We do that by incrementing to the next month (in case
                    # it's on a year boundary, we don't have to bother with that), and
                    # replacing day with the last day of the month again
                    next_due_on_day = next_due_on_day + relativedelta(days=1)
                    next_due_on_day = next_due_on_day.replace(
                        day=calendar.monthrange(
                            next_due_on_day.year, next_due_on_day.month
                        )[-1]
                    )
                else:
                    # Otherwise, it's just incrementing days
                    next_due_on_day = next_due_on_day + relativedelta(
                        **{interval.name.lower(): frequency}  # type: ignore
                    )

            logger.info(
                f"For day {d}, interval {interval.name}, next due on this day: {next_due_on_day}"
            )

            # Finally, if the next date it's due on this day is less than the latest
            # due date seen so far, set this as the latest due date.
            if next_due_on_day < latest_due:
                logger.info(
                    f"Replacing latest due {latest_due} with next due on this day: {next_due_on_day}"
                )
                latest_due = next_due_on_day

        next_due_date = latest_due

    # This is probably already done, but just be safe here.
    if at_time is not None:
        ret: Union[datetime, date] = next_due_date.replace(
            hour=at_time.hour, minute=at_time.minute, second=0, microsecond=0
        )
    else:
        ret = date(
            year=next_due_date.year,
            month=next_due_date.month,
            day=next_due_date.day,
        )
    logger.info(
        f"Next due date with base {base}, interval {interval.name}, frequency {frequency}, at_time {at_time}, and days {days}: {next_due_date}"
    )
    return ret


def get_base(
    task: Task,
    start_from: Optional[StartFrom] = None,
    days: Optional[List[int]] = None,
) -> datetime:
    """Get the base, given a task and an optional specification of when to start
    from."""
    logger.info(
        f"Getting base time for task {task.name}, starting from {start_from}, with days {days}"
    )

    # Figure out what the base time we want is. If we have "start from", it'll tell us
    # to use one of the due date, or completed date. For now, `last_edited_time` will
    # have to approximate completed date.
    #
    # If we don't have "start from", the base will depend on if specific days have been
    # asked for.
    base: Optional[Union[date, datetime]] = None
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

    # If our base is, in fact, a date, let's convert it to a datetime for everything
    # downstream. Internally, we operate on datetimes, but we allow either datetimes or
    # dates as input, and output either a datetime or date.
    if not isinstance(base, datetime):
        base = datetime.combine(base, time()).astimezone()

    return base.astimezone()


def handle_special_cases(to_parse: str) -> str:
    """Handle special case strings. We just convert them to known format
    so our generic parsers can handle them:
        - Every (day/weekday) (at 9am)
        - Every (Mon/Tue/Weds...) (at 9am)"""
    s = to_parse.lower()
    if s.startswith("every day"):
        return s.replace("every day", "Every 1 days")
    elif s.startswith("every weekday"):
        return s.replace("every weekday", "Every 1 weeks, on 1-5")
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
        raise Exception(f"Failed to parse start from string '{to_parse}', error: {e}")


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
            return check_numerics(numeric_values, 1, 7)

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

        return check_numerics(parse_numerics(to_parse), 1, 7)
    except Exception as e:
        raise Exception(f"Failed to parse weekdays string '{to_parse}', error: {e}")


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
        raise Exception(f"Failed to parse days string '{to_parse}', error: {e}")


def parse_numerics(to_parse: str) -> List[int]:
    """Parse a string containing numeric values and return a list of integers."""
    try:
        # Split the string, and filter into ranges and values
        parts = to_parse.split("/")
        ranges = list(filter(lambda s: "-" in s, parts))

        # Immediately add any hardcoded numbers
        numeric_values = [int(v) for v in filter(lambda s: "-" not in s, parts)]

        # Parse ranges and add them as well
        for r in ranges:
            i, n = [int(s) for s in r.split("-")]
            numeric_values.extend(range(i, n + 1))

        return sorted(numeric_values)
    except Exception as e:
        raise Exception(
            f"Failed to parse numeric literal string: '{to_parse}', error: {e}"
        )


def get_next_due_date(task: Task) -> Union[datetime, date]:
    """Given a task, figure out what its next due date will be based on its schedule. In its
    most basic form, a schedule will just be a Cron string. However, it may also take the following
    forms:
        - Every (X) (days|weeks|months|years)
        - Every (X) (days|weeks|months|years), at (9am)
        - Every (X) (days|weeks|months|years), from (due date/completed date)
        - Every (X) (days|weeks|months|years), from (due date/completed date), at (9am)
        - Every (X) (days|weeks|months|years), at (9am), from (due date/completed date)
        - Every (X) weeks, on (mon/tue/wed, etc.)
        - Every (X) weeks, on (mon/tue/wed, etc.), at (9am)
        - Every (X) months, on the last day
        - Every (X) months, on the last day, at (9am)
        - Every (X) (weeks|months|years), on day (1/3/5-7)
        - Every (X) (weeks|months|years), on day (1/3/5-7), at (9am)
        - Every (X) (weeks|months|years), at (9am), on day (X)
        - Every (day|weekday)
        - Every (day|weekday), at (9am)
        - Every (mon/tue/wed, etc.)
        - Every (mon/tue/wed, etc.), at (9am)

    where values in parentheses are specified by the user.

    NOTE: The syntax in these strings is extremely important. Our parser expects that each part
    of the schedule be separated by a comma, and that consecutive elements of lists be separated
    by forward slashes (/). Some examples of valid strings are:
        - "Every mon/tuesday, at 9am" (equivalent to "Every 1 weeks, on day 1/2, at 9am")
        - "Every 1 months, on day 1/5-9" ("5-9" will be interpreted as a range, meaning the schedule
            should execute on days 1, 5, 6, 7, 8, and 9)
        - "Every 1 months, on day 1"
        - "Every 1 months, on the last day"

    To specify days of the week, you may use either abbreviations (e.g. mon, tue) or the full day
    name (monday, tuesday). Time (9am) must be in dateutil-compatible string format.

    If "from (due date/completed date)" is not specified, we will choose a default, depending on
    the configuration. Note that you cannot specify _*both*_ "start from" _*and*_ specific days to
    execute on."""

    if task.schedule is None:
        raise Exception(f"Task '{task.name}' has no schedule")

    # Check if it's an expression that croniter can handle, or if we need to process
    # ourselves.
    if croniter.is_valid(task.schedule):
        # croniter's got this
        logger.info(
            f"Task {task.name} has a cron-compatible schedule - deferring to croniter"
        )
        base = datetime.now().astimezone()
        iter = croniter(task.schedule, base)
        return iter.get_next(datetime)
    else:
        # Process with the schedule utility
        logger.info(f"Task {task.name} has a custom schedule - parsing")
        schedule = Schedule(task)
        return schedule.get_next()
