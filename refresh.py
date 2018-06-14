#!/usr/bin/env python3

import sys
import datetime
from datetime import datetime as dt

verbose = True

def read_block_file (filename):
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

def refresh (filename, blocks):
    ''' main function to correct the hosts file. '''
    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    now = dt.time(dt.now())
    day_start = datetime.time(0, 0)
    day_end = datetime.time(23, 59)
    newdata = data[:]

    for group in blocks:
        if verbose: print('group', group['name'], '(', group['start'], '->', group['end'], '):')
        # check time constraints
        within_time = False
        if group['start'] < group['end']:
            within_time = now > group['start'] and now < group['end']
        else:
            within_time = (now >= group['start'] and now <= day_end) or \
                          (now <= group['end']   and now >= day_start)

        if within_time:
            # construct lines of new file
            blockentries = [ '0.0.0.0\t'+i+'\n' for i in group['list'] ]
            for entry in blockentries:
                if entry not in data:
                    if '#'+entry in data:
                        # uncomment the line
                        if verbose: print('\t', entry[:-1], 'is commented at line', data.index('#'+entry))
                        newdata[data.index('#'+entry)] = entry
                    else:
                        # add the line
                        if verbose: print('\t', entry[:-1], 'is missing')
                        newdata.append(entry)
        elif verbose: print('\t not in time range', group['start'], '->',  group['end'])

    if data == newdata:
        # file has not changed - don't bother writing
        if verbose: print('-- nothing\'s changed!')
    else:
        # update the file
        with open(filename, 'w') as f:
            f.writelines(newdata)
        if verbose: print('-- refreshed')

def main ():
    if verbose: print('-- refreshing', sys.argv[1], 'using blocklist', sys.argv[2])
    to_refresh = sys.argv[1]
    blocks = read_block_file(sys.argv[2])
    refresh(to_refresh, blocks)

if __name__ == '__main__':
    main()
