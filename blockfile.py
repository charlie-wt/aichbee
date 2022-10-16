import datetime
from datetime import datetime as dt
import os

from blockgroup import BlockGroup
import blocktime as bt
import parse


verbose = False


def get_filename () -> str:
    '''
    try to get the blockfile from a standard location; /etc/hb/blocklist if running as
    root, otherwise tries to use $XDG_CONFIG_HOME (in normal usage should be running as
    root, since we're modifying /etc/hosts).

    ... not the neatest thing.

    '''

    prefix = '/etc'

    if os.geteuid() != 0:
        var = os.environ.get('HOME')
        if var is not None:
            prefix = var + '/.config'
        var = os.environ.get('XDG_CONFIG_HOME')
        if var is not None and (os.path.isdir(var)):
            prefix = var

    return prefix + '/hb/blocklist'


def read (filename: str = None) -> [BlockGroup]:
    ''' read a list of domains to block (like 'blocklist'), from a file. '''

    if filename is None:
        filename = get_filename()

    blockgroups = []

    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    # get just the blocked domains
    current_group = None
    in_group = False
    for line in data:
        if line == '\n' or line[0] == '#': continue
        if line[-1] == '\n': line = line[:-1]

        if line[0] == "=":
            # lines starting with '=' mark the start/end of block groups
            if in_group:
                in_group = False
            else:
                in_group = True
                name = line[1:] if line[1] != ' ' else line[2:]
                blockgroups.append(BlockGroup(name))
                current_group = blockgroups[-1]
        elif in_group:
            if line[0] == '@':
                parse.constraint_line(line, current_group, verbose)

                if not constraints_consistent(current_group):
                    n = (current_group.name if current_group.name else '')
                    raise ValueError('time constraints on block group ' + \
                                     n + ' overlap, and so are not consistent.')
            else:
                current_group.sites.append(line)

    # add www./non www. versions if necessary
    for group in blockgroups:
        orig = group.sites[:]
        group.sites += [ 'www.'+i for i in orig if not i.startswith('www.') ]
        group.sites += [ i[4:] for i in orig if i.startswith('www.') ]

    # return results
    return blockgroups


def constraints_consistent (group: BlockGroup) -> bool:
    '''
    Are the constraints on the given block group consistent with each other?

    Currently, returns `False` if any of the time-only constraints (eg. "@ 01:00 -
    02:00") *or* any of the day-based constraints (eg. "@ mon 03:00 - fri 04:00")
    overlap at all in time (they're checked independently).

    '''

    def indices_consistent (group: BlockGroup, indices: [int]) -> bool:
        ''' is the given set of indices consistent with itself? '''

        for i in indices:
            for j in indices:
                if i == j:
                    continue

                bad_start = bt.within_time(
                    now=group.starts[i], starts=[group.starts[j]], ends=[group.ends[j]])
                bad_end = bt.within_time(
                    now=group.ends[i], starts=[group.starts[j]], ends=[group.ends[j]])

                if bad_start or bad_end:
                    if verbose:
                        print(f'constraints for group {group.name}:',
                              f'{group.starts[i]} -> {group.ends[i]}',
                              f'vs. {group.starts[j]} -> {group.ends[j]}:',
                              f'bad start: {bad_start}, bad end: {bad_end}')
                    return False
        return True

    time_only_indices = \
        [ i for i in range(len(group.starts)) if group.starts[i].day is None ]
    if not indices_consistent(group, time_only_indices):
        return False

    day_based_indices = \
        [ i for i in range(len(group.starts)) if group.starts[i].day is not None ]
    if not indices_consistent(group, day_based_indices):
        return False

    return True
