from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime as dt
import re

from blockgroup import BlockGroup, Duration, DurationPeriod
from blocktime import Time, TimeRange, Weekday


NAME_PAT = re.compile(r'\s*=\s*(?P<name>.*)\s*')


def parse_name (line: str) -> str | None:
    if m := re.match(NAME_PAT, line):
        return m.group('name')
    return None


def parse_time_constraint (m: re.Match, group: BlockGroup):
    start = Time.from_str(time_str=m.group('start_time'))
    end = Time.from_str(time_str=m.group('end_time'))

    group.schedule_ranges.append(TimeRange(start, end))


def parse_day_constraint (m: re.Match, group: BlockGroup):
    start = Time.from_str(time_str=m.group('start_time'),
                          day=Weekday.from_str(m.group('start_day')))
    end = Time.from_str(time_str=m.group('end_time'),
                        day=Weekday.from_str(m.group('end_day')))

    group.schedule_ranges.append(TimeRange(start, end))


@dataclass
class LineType:
    regex: re.Pattern
    handler: Callable[[re.Match, BlockGroup], None]


SCHEDULE_HANDLERS = [
    LineType(re.compile(r'\s*@\s*'
                        r'(?P<start_time>\d\d:\d\d)\s*-\s*'
                        r'(?P<end_time>\d\d:\d\d)\s*'),
             parse_time_constraint),
    LineType(re.compile(r'\s*@\s*'
                        r'(?P<start_day>\w+)\s*'
                        r'(?P<start_time>\d\d:\d\d)\s*-\s*'
                        r'(?P<end_day>\w+)\s*'
                        r'(?P<end_time>\d\d:\d\d)\s*'),
             parse_day_constraint),
]


def parse_schedule_constraint (line: str, group: BlockGroup) -> None:
    ''' add the parsed schedule-constraint line `line` to BlockGroup `group`, or raise a
    ValueError.
    '''
    for h in SCHEDULE_HANDLERS:
        if m := re.match(h.regex, line):
            h.handler(m, group)
            return
    raise ValueError(f"Block group {group.display_name()}: couldn't parse blockfile "
                     f"line: '{line}'")


DURATION_PAT = re.compile(r'<(?P<length>\d+)hr\s+per\s+(?P<period>\w+)')


def parse_duration_constraint (line: str, group: BlockGroup) -> None:
    if group.duration is not None:
        raise ValueError("Can only have one duration-based constraint per block "
                         "group, but tried to parse multiple on "
                         f"{group.display_name()}.")

    m = re.match(DURATION_PAT, line)
    if m is None:
        raise ValueError(f"Block group {group.display_name()}: couldn't parse "
                         f"blockfile line: '{line}'")

    group.duration = Duration(DurationPeriod.from_str(m.group("period")),
                              float(m.group("length")))
