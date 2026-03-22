from dataclasses import dataclass, field
from datetime import datetime as dt
from enum import Enum, auto
from functools import total_ordering

import util


@total_ordering
class Weekday(Enum):
    MONDAY    = 0   # start from 0 so we can cast from result of datetime.weekday()
    TUESDAY   = auto()
    WEDNESDAY = auto()
    THURSDAY  = auto()
    FRIDAY    = auto()
    SATURDAY  = auto()
    SUNDAY    = auto()

    def from_dt (dtime: dt) -> 'Weekday':
        return Weekday(dtime.weekday())

    def now () -> 'Weekday':
        return Weekday.from_dt(dt.today())

    def from_str (string: str) -> 'Weekday':
        ''' Parse ``string`` into a ``Weekday`` (based on it being the prefix of a
        weekday), or raise a ``ValueError`` if it can't be done.
        '''
        return util.get_unique_enum_prefix_match(
            string, Weekday, value_name="weekday")

    def __lt__ (self, other: 'Weekday') -> bool:
        return self.value < other.value


@dataclass
class Time:
    time: dt.time
    day: Weekday | None = None

    def __str__ (self):
        return f'{self.day.name.title()[:3] + " @ " if self.day else ""}' \
               f'{self.time.strftime("%H:%M")}'

    def from_dt (dtime: dt) -> 'Time':
        return Time(dt.time(dtime), Weekday.from_dt(dtime))

    def now () -> 'Time':
        return Time.from_dt(dt.now())

    def from_str (time_str: str, day: Weekday | None = None) -> 'Time':
        ''' Expects a string of the format hh:mm '''
        return Time(time=dt.strptime(time_str, '%H:%M').time(), day=day)


@dataclass
class TimeRange:
    start: Time
    end: Time

    def __post_init__ (self):
        if (self.start.day is None) != (self.end.day is None):
            raise ValueError('Constraint time range: either *both* the start and end '
                             'should have a weekday, or *neither* should have a '
                             f'weekday, but got {self}.')

    def __str__ (self):
        return f'{self.start} -> {self.end}'

    def time_only (self) -> bool:
        return self.start.day is None


def within_constraints (now: Time | None, ranges: list[TimeRange] | TimeRange) -> bool:
    '''
    Check a time against constraints.

    If `now` is `None`, use current system time.
    If `now.day` is `None`, but there are day-based constraints, will return `False`.

    '''

    if now is None: now = Time.now()

    if not isinstance(ranges, list): ranges = [ranges]
    if len(ranges) == 0: return True

    for r in ranges:
        # do we not have to worry about day-level constraints (no constraints, or all on
        # the same day)?
        use_time_only = r.time_only() or \
            (now.day is not None and now.day == r.start.day == r.end.day)
        if use_time_only:
            if r.start.time <= r.end.time:
                if r.start.time <= now.time <= r.end.time:
                    return True
            else:
                # wraparound
                if now.time >= r.start.time or now.time <= r.end.time:
                    return True
            continue

        if now.day is None:  # we're now dealing with day constraints, so we need a day.
            return False

        # are we on a 'border day' of the day-based constraints? if so, check the times.
        if now.day == r.start.day:
            if now.time >= r.start.time:
                return True
            continue
        if now.day == r.end.day:
            if now.time <= r.end.time:
                return True
            continue

        # are we completely inside the day-based constraints?
        if r.start.day == r.end.day:
            # wraparound (we've already covered the non-wraparound & time-based-checking
            # cases at the top)
            if r.start.time > r.end.time and now.day != r.start.day:
                return True
        elif r.start.day < r.end.day:
            if r.start.day < now.day < r.end.day:
                return True
        else:
            if now.day > r.start.day or now.day < r.end.day:  # wraparound
                return True

    return False
