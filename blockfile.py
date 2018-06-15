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
    current_block = None
    # get just the blocked domains
    in_group = False
    for line in data:
        if line == '\n' or line[0] == '#': continue
        if line[-1] == '\n': line = line[:-1]

        if line[0] == "=":
            # lines beginning with '=' mark the start & end of individual block groups
            if in_group:
                in_group = False
            else:
                in_group = True
                name = line[1:] if line[1] != ' ' else line[2:]
                blockgroups.append({ 'name': name, 'list': [], 'start': None, 'end': None })
                current_block = blockgroups[-1]
        elif in_group:
            if line[0] == '@':
                # line beginning with @: time range in which to apply the blocks
                l = line.replace(' ', '')
                start_str = l[1:l.index('-')]
                end_str = l[l.index('-')+1:len(l)]
                block_start = dt.strptime(start_str, '%H:%M').time()
                block_end = dt.strptime(end_str, '%H:%M').time()
                if verbose: print(block_start, '->', block_end)
                current_block['start'] = block_start
                current_block['end'] = block_end
            else:
                current_block['list'].append(line)

    # add www./non www. versions if necessary
    for group in blockgroups:
        orig = group['list'][:]
        group['list'] += [ 'www.' + item for item in orig if not item.startswith('www.') ]
        group['list'] += [ item[4:] for item in orig if item.startswith('www.') ]

    # if verbose: print(blockgroups)

    # return results
    return blockgroups
