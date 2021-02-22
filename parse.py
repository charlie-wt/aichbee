from datetime import datetime as dt
import re

from blockgroup import BlockGroup
from blocktime import Weekday, Time


def constraint_line (line: str, group: BlockGroup, verbose: bool = False):
    if re.match('.*[a-zA-Z].*', line) is not None:
        # if there are words on the line, they're day names.
        day_line(line, group, verbose)
    else:
        time_line(line, group)


def time_line (line: str, group: BlockGroup):
    l = line.replace(' ', '').replace('\t', '')

    start_str = l[1:l.index('-')]
    end_str   = l[l.index('-')+1:]

    block_start = dt.strptime(start_str, '%H:%M').time()
    block_end   = dt.strptime(end_str, '%H:%M').time()

    group.starts.append(Time(block_start))
    group.ends.append(Time(block_end))


def day_line (line: str, group: BlockGroup, verbose: bool = False):
    l = line.replace(' ', '').replace('\t', '')

    # get the string components
    start_str = l[1:l.index('-')]
    end_str   = l[l.index('-')+1:]

    start_day_str  = start_str[:3]
    start_time_str = start_str[3:]

    end_day_str  = end_str[:3]
    end_time_str = end_str[3:]

    # make data structures
    start_time = dt.strptime(start_time_str, '%H:%M').time()
    end_time   = dt.strptime(end_time_str, '%H:%M').time()

    start_day = day(start_day_str)
    end_day   = day(end_day_str)

    if start_day is None or end_day is None:
        if verbose:
            print('error parsing day constaints ("'
                  + start_day_str + '"-"' + end_day_str + '") of block group.')
        return

    # append to input group
    group.starts.append(Time(start_time, start_day))
    group.ends.append(Time(end_time, end_day))


def day (string: str) -> Weekday:
    string = string.lower()
    if string == 'mon':
        return Weekday.MONDAY
    if string == 'tue':
        return Weekday.TUESDAY
    if string == 'wed':
        return Weekday.WEDNESDAY
    if string == 'thu':
        return Weekday.THURSDAY
    if string == 'fri':
        return Weekday.FRIDAY
    if string == 'sat':
        return Weekday.SATURDAY
    if string == 'sun':
        return Weekday.SUNDAY
    return None
