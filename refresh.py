#!/usr/bin/env python3

import sys
import datetime
from datetime import datetime as dt

verbose = False

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
        if line[-1] == '\n':
            line = line[:-1]
        if line[0] == "=":
            # lines beginning with '=' mark the start & end of individual block groups
            if in_group:
                in_group = False
            else:
                in_group = True
                blockgroups.append({ 'list': [], 'start': None, 'end': None })
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
    if verbose: print('refreshing')
    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    # TODO #temporary: assumes only one block group
    group = blocks[0]
    within_time = False
    now = dt.time(dt.now())
    midnight = datetime.time(0, 0)
    if group['start'] < group['end']:
        within_time = now > group['start'] and now < group['end']
    else:
        within_time = (now > group['start'] and now < midnight) or \
                      (now < group['end']   and now > midnight)

    if within_time:
        # construct lines of new file
        blockentries = [ '0.0.0.0\t'+i+'\n' for i in group['list'] ]
        newdata = data[:]
        for entry in blockentries:
            if entry not in data:
                if '#'+entry in data:
                    # uncomment the line
                    if verbose: print(entry[:-1], 'is commented at line', data.index('#'+entry))
                    newdata[data.index('#'+entry)] = entry
                else:
                    # add the line
                    if verbose: print(entry[:-1], 'is missing')
                    newdata.append(entry)
            else:
                if verbose: print(entry[:-1], 'is present, at line', data.index(entry))

        if data == newdata:
            # file has not changed - don't bother writing
            if verbose: print('nothing\'s changed!')
        else:
            # update the file
            with open(filename, 'w') as f:
                f.writelines(newdata)
            print('refreshed')
    elif verbose: print('not in time range', group['start'], '->',  group['end'])

def main ():
    if verbose: print('refreshing', sys.argv[1], 'using blocklist', sys.argv[2])
    to_refresh = sys.argv[1]
    blocklist = read_block_file(sys.argv[2])
    refresh(to_refresh, blocklist)

if __name__ == '__main__':
    main()
