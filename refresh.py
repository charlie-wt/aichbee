#!/usr/bin/env python3

import sys
prnt = False

def read_block_file (filename):
    ''' read a list of domains to block (like 'blocklist'), from a file '''
    blocklist = []

    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    # get just the blocked domains
    reading_blocks = False
    for line in data:
        if line[-1] == '\n':
            line = line[:-1]
        if line == '= DOMAINS':
            reading_blocks = True
        elif reading_blocks:
            if line == '===':
                reading_blocks = False
            else:
                blocklist.append(line)

    # add www./non www. versions if necessary
    orig = blocklist[:]
    blocklist += [ 'www.' + item for item in orig if not item.startswith('www.') ]
    blocklist += [ item[4:] for item in orig if item.startswith('www.') ]

    if prnt: print(blocklist)

    # return results
    return blocklist

def refresh (filename, blocklist):
    ''' main function to correct the hosts file. '''
    if prnt: print('refreshing')
    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    # construct lines of new file
    blockentries = [ '0.0.0.0\t'+i+'\n' for i in blocklist ]
    newdata = data[:]
    for entry in blockentries:
        if entry not in data:
            if '#'+entry in data:
                # uncomment the line
                if prnt: print(entry[:-1], 'is commented at line', data.index('#'+entry))
                newdata[data.index('#'+entry)] = entry
            else:
                # add the line
                if prnt: print(entry[:-1], 'is missing')
                newdata.append(entry)
        else:
            if prnt: print(entry[:-1], 'is present, at line', data.index(entry))

    if data == newdata:
        # file has not changed - don't bother writing
        if prnt: print('nothing\'s changed!')
    else:
        # update the file
        with open(filename, 'w') as f:
            f.writelines(newdata)
        if prnt: print('refreshed')

def main ():
    if prnt: print('refreshing', sys.argv[1], 'using blocklist', sys.argv[2])
    to_refresh = sys.argv[1]
    blocklist = read_block_file(sys.argv[2])
    refresh(to_refresh, blocklist)

if __name__ == '__main__':
    main()
