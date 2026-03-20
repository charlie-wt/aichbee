from datetime import datetime as dt
import os
from pathlib import Path

from blockgroup import BlockGroup
import blocktime as bt
import parse


def get_filename (allow_nonroot_fallback: bool = False) -> str:
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

    prefix = os.path.abspath(os.path.join(os.path.sep, 'etc'))

    if allow_nonroot_fallback and os.geteuid() != 0:
        var = os.environ.get('HOME')
        if var is not None:
            prefix = os.path.join(var, '.config')
        var = os.environ.get('XDG_CONFIG_HOME')
        if var is not None and (os.path.isdir(var)):
            prefix = var

    return os.path.join(prefix, 'aichbee', 'blockfile')


def read (filename: str | Path) -> list[BlockGroup]:
    ''' read a list of domains to block (like `example-blockfile`) from a file. '''

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
                blockgroups.append(BlockGroup(parse.parse_name(line)))
                current_group = blockgroups[-1]
        elif in_a_group:
            if line[0] == '@':
                parse.parse_constraint(line, current_group)

                if not current_group.constraints_consistent():
                    raise ValueError(f'time constraints on block group '
                                     f'{n.display_name()} overlap, and so are not '
                                     'consistent.')
            else:
                current_group.sites.append(line)

    # add www./non www. versions if necessary
    for group in blockgroups:
        orig = group.sites[:]
        group.sites += [ 'www.'+i for i in orig if not i.startswith('www.') ]
        group.sites += [ i[4:] for i in orig if i.startswith('www.') ]

    # return results
    return blockgroups
