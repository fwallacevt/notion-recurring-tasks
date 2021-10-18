"""Test the schedule utility."""

from utils.schedule import (
    parse_days,
    parse_frequency_and_interval,
    parse_numerics,
    parse_start_from,
    parse_weekdays,
)

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
