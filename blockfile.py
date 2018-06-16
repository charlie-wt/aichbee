import datetime
from datetime import datetime as dt

verbose = False

def read (filename):
    ''' read a list of domains to block (like 'blocklist'), from a file '''
    blockgroups = []

    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    # TODO #functionality: allow multiple time constraint rules?
    #                      - would need to check consistency, I think
    block_start = None
    block_end = None
    block_starts = None
    block_ends = None
    current_group = None
    # get just the blocked domains
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
                blockgroups.append(
                    { 'name': name, 'list': [], 'start': None, 'end': None, 'starts': [], 'ends': [] }
                )
                current_group = blockgroups[-1]
        elif in_group:
            if line[0] == '@':
                # line beginning with @: time range in which to apply the blocks
                l = line.replace(' ', '')
                start_str = l[1:l.index('-')]
                end_str = l[l.index('-')+1:len(l)]
                block_start = dt.strptime(start_str, '%H:%M').time()
                block_end = dt.strptime(end_str, '%H:%M').time()
                current_group['start'] = block_start
                current_group['end'] = block_end
                current_group['starts'].append(block_start)
                current_group['ends'].append(block_end)
                if not constraints_consistent(current_group):
                    n = (current_group['name'] if current_group['name'] else '')
                    raise ValueError('time constraints on block group ' + \
                                     n + ' are not consistent.')
            else:
                current_group['list'].append(line)

    # add www./non www. versions if necessary
    for group in blockgroups:
        orig = group['list'][:]
        group['list'] += [ 'www.'+i for i in orig if not i.startswith('www.') ]
        group['list'] += [ i[4:] for i in orig if i.startswith('www.') ]

    # if verbose: print(blockgroups)

    # return results
    return blockgroups

def constraints_consistent (group):
    # time
    name = (group['name'] if group['name'] else '')
    pref = 'constraints for group '+name+':'
    for i in range(len(group['starts'])):
        for j in range(len(group['starts'])):
            if i != j:
                bad_start = group['starts'][i] > group['starts'][j] and \
                            group['starts'][i] < group['ends'][j]
                bad_end = group['ends'][i] > group['starts'][j] and \
                          group['ends'][i] < group['ends'][j]

                if bad_start or bad_end:
                    if verbose:
                        print(pref, group['starts'][i], '->', group['ends'][i],
                              'vs.',group['starts'][j], '->', group['ends'][j],
                              ': bad start:', bad_start, ', bad end:', bad_end)
                    return False

    return True
