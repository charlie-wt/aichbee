from enum import Enum, auto
import re

from blockgroup import BlockGroup


verbose = False

def log (*args, **kwargs):
    if verbose: print(*args, **kwargs)


class BlockedState(Enum):
    ''' The state of a given blocked site in the watched file (ie. `hosts`). '''
    BLOCKED = auto()
    COMMENTED = auto()
    ABSENT = auto()


def blocked_state (site: str, watchfile_lines: list[str]) -> (BlockedState, list[int]):
    '''
    Get the state of the given site, within the given 'watch file' lines (eg. those
    of `hosts`)

    '''

    blocked_regex = re.compile('0.0.0.0\s+' + site)
    commented_regex = re.compile('#\s*0.0.0.0\s+' + site)

    blocked_lines = []
    commented_lines = []

    blocked = False

    # get the lines of `watchfile_lines` that contain (un)commented entries for `site`
    for n,l in enumerate(watchfile_lines):
        if blocked_regex.match(l):
            blocked = True
            blocked_lines.append(n)

        if blocked:
            continue

        if commented_regex.match(l):
            commented_lines.append(n)

    # return list of line numbers based on blocked status of `site`.
    if blocked:
        return (BlockedState.BLOCKED, blocked_lines)
    elif len(commented_lines) > 0:
        return (BlockedState.COMMENTED, commented_lines)
    else:
        return (BlockedState.ABSENT, [])


def block (filename: str, blocks: list[BlockGroup] | BlockGroup):
    ''' Main function to correct the hosts file. '''
    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    newdata = data[:]
    if not isinstance(blocks, list): blocks = [blocks]

    for group in blocks:
        log('group', group.display_name(), ':')

        if not group.within_constraints():
            log('\t not in time range')
            continue

        # this site should be blocked -- construct lines of new file
        for site in group.sites:
            state, lines = blocked_state(site, data)

            # site is already blocked
            if state == BlockedState.BLOCKED:
                continue

            entry = '0.0.0.0\t' + site + '\n'

            # site is commented out -- uncomment
            if state == BlockedState.COMMENTED:
                log('\t', entry[:-1], 'is commented on lines', lines)
                for l in lines:
                    newdata[l] = entry
                continue

            # site is absent -- add
            log('\t', entry[:-1], 'is missing')
            newdata.append(entry)

    if data == newdata:
        # file has not changed - don't bother writing
        log('-- nothing\'s changed!')
    else:
        # update the file
        with open(filename, 'w') as f:
            f.writelines(newdata)
        log('-- blocked')


def unblock (filename: str, blocks: list[BlockGroup] | BlockGroup):
    '''
    Unblock all websites in the blocks, applied one-by-one. To be used after
    a schedule finishes.

    '''

    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    newdata = data[:]
    if not isinstance(blocks, list): blocks = [blocks]

    for group in blocks:
        log(f'unblocking group {group.display_name()}:')

        # construct lines of new file
        blockentries = [ '#0.0.0.0\t'+i+'\n' for i in group.sites ]
        for entry in blockentries:
            if entry not in data:
                if entry[1:] in data:
                    # comment the line
                    if verbose:
                        print('\t', entry[1:-1], 'is active at line',
                              data.index(entry[1:]))
                    newdata[data.index(entry[1:])] = entry

    if data == newdata:
        # file has not changed - don't bother writing
        log('-- nothing\'s changed!')
    else:
        # update the file
        with open(filename, 'w') as f:
            f.writelines(newdata)
        log('-- unblocked')
