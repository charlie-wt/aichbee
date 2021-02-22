from dataclasses import dataclass, field
import datetime
from datetime import datetime as dt
from enum import Enum, auto
from functools import total_ordering


@total_ordering
class Weekday(Enum):
    MONDAY    = 0   # start from 0 so we can cast from result of datetime.weekday()
    TUESDAY   = auto()
    WEDNESDAY = auto()
    THURSDAY  = auto()
    FRIDAY    = auto()
    SATURDAY  = auto()
    SUNDAY    = auto()

    def now () -> 'Weekday':
        return Weekday(dt.today().weekday())

    def __lt__ (self, other: 'Weekday') -> bool:
        return self.value < other.value


@dataclass
class Time:
    time: dt.time
    day: Weekday = None

    def now () -> 'Time':
        return Time(dt.time(dt.now()), Weekday.now())


def within_time (now: Time, starts: [Time], ends: [Time]) -> bool:
    '''
    Check time constraints.

    If `now` is `None`, will be set to current system time.

    If `now.day` is `None`, but there are day-based constraints, will return `False`.

    '''

    if now is None: now = Time.now()

    if starts == [] or ends == []:
        return True

    for i in range(len(starts)):
        # do we not have to worry about day-level constraints (no constraints, or all on
        # the same day)?
        use_time_only = starts[i].day is None or ends[i].day is None
        use_time_only = use_time_only or \
            (now.day is not None and now.day == starts[i].day == ends[i].day)
        if use_time_only:
            # don't care about days -- check by time constraint only.
            if starts[i].time < ends[i].time:
                if now.time >= starts[i].time and now.time <= ends[i].time:
                    return True
            else:
                if now.time >= starts[i].time or now.time <= ends[i].time:  # wraparound
                    return True
            continue

        if now.day is None:  # we're now dealing with day constraints, so we need a day.
            return False

        # are we on a 'border day' of the day-based constraints? if so, check the times.
        if now.day == starts[i].day:
            if now.time >= starts[i].time:
                return True
            continue
        if now.day == ends[i].day:
            if now.time <= ends[i].time:
                return True
            continue

        # are we completely inside the day-based constraints?
        if starts[i].day == ends[i].day:
            if starts[i].time < ends[i].time:
                if now.day > starts[i].day and now.day < ends[i].day:
                    return True
            else:
                if now.day > starts[i].day or now.day < ends[i].day:  # wraparound
                    return True
        elif starts[i].day < ends[i].day:
            if now.day > starts[i].day and now.day < ends[i].day:
                return True
        else:
            if now.day > starts[i].day or now.day < ends[i].day:  # wraparound
                return True

    return False
