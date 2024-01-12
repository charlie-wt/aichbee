from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime as dt
import re

from blockgroup import BlockGroup
from blocktime import Time, TimeRange, Weekday


NAME_PAT = re.compile(r'\s*=\s*(.*)\s*')


def parse_name (line: str) -> str | None:
    if m := re.match(NAME_PAT, line):
        return m.group(1)
    return None


def parse_time_constraint (m: re.Match, group: BlockGroup):
    start = Time.from_str(time_str=m.group('start_time'))
    end = Time.from_str(time_str=m.group('end_time'))

    group.ranges.append(TimeRange(start, end))


def parse_day_constraint (m: re.Match, group: BlockGroup):
    start = Time.from_str(time_str=m.group('start_time'), day=day(m.group('start_day')))
    end = Time.from_str(time_str=m.group('end_time'), day=day(m.group('end_day')))

    group.ranges.append(TimeRange(start, end))


@dataclass
class LineType:
    regex: re.Pattern
    handler: Callable[[re.Match, BlockGroup], None]


HANDLERS = [
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


def parse_constraint (line: str, group: BlockGroup) -> None:
    ''' add the parsed constraint line `line` to BlockGroup `group`, or raise a
    ValueError.
    '''
    for h in HANDLERS:
        if m := re.match(h.regex, line):
            h.handler(m, group)
            return
    raise ValueError(f"Couldn't parse blocklist line: '{line}'")


def day (string: str) -> Weekday:
    ''' parse `string` into a Weekday (based on it being the prefix of a weekday), or
    raise a ValueError.
    '''
    s = string.lower()
    for d in Weekday:
        if d.name.lower().startswith(s):
            return d

    raise ValueError(f"Couldn't parse weekday '{string}'")
