from datetime import datetime as dt
import os
from pathlib import Path

from blockgroup import BlockGroup
import blocktime as bt
import parse
import util


def get_filename (allow_nonroot_fallback: bool = False) -> Path:
    '''
    try to get the blockfile from a standard location.

    normally this will be /etc/aichbee/blockfile (in normal usage should be running as
    root, since we're modifying /etc/hosts). however, in some circumstances can return
    something under $XDG_CONFIG_HOME (see ``allow_nonroot_fallback``).

    ... not the neatest thing.

    :param allow_nonroot_fallback: If True, and this function is being run by a non-root
                                   user, return an alternative path under
                                   $XDG_CONFIG_HOME; otherwise, will always return the
                                   system location.

    '''

    path = Path('/etc/aichbee')

    if allow_nonroot_fallback and os.geteuid() != 0:
        path = util.config_dir()

    return path / 'blockfile'


def read (filename: str | Path, load_state: bool = True) -> list[BlockGroup]:
    ''' read a list of domains to block (like `example-blockfile`) from a file.

    :param filename: Path to read from.
    :param load_state: Whether to also try to load the state file for this group, to
                       maintain things like remaining durations.
    '''

    if isinstance(filename, Path):
        filename = str(filename.resolve())

    blockgroups = []

    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    # get just the blocked domains
    current_group: BlockGroup | None = None
    in_a_group = False
    for line in data:
        line = line.split('#', 1)[0].strip()
        if line == '': continue

        if line[0] == "=":
            # lines starting with '=' mark the start/end of block groups
            if in_a_group:
                in_a_group = False
            else:
                in_a_group = True
                blockgroups.append(BlockGroup(parse.parse_name(line),
                                              config_filename=filename))
                current_group = blockgroups[-1]
        elif in_a_group:
            if line[0] == '@':
                parse.parse_schedule_constraint(line, current_group)

                if not current_group.schedule_constraints_consistent():
                    raise ValueError(f'time constraints on block group '
                                     f'{n.display_name()} overlap, and so are not '
                                     'consistent.')
            elif line[0] == '<':
                parse.parse_duration_constraint(line, current_group)
            else:
                current_group.sites.append(line)

    # add www./non www. versions if necessary
    for group in blockgroups:
        orig = group.sites[:]
        group.sites += [ 'www.'+i for i in orig if not i.startswith('www.') ]
        group.sites += [ i[4:] for i in orig if i.startswith('www.') ]

    if load_state:
        for group in blockgroups:
            group.load_state()

    # return results
    return blockgroups
