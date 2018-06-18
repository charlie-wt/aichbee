import datetime
from datetime import datetime as dt

verbose = False

def within_time (group=None, now=None, starts=None, ends=None):
    ''' check time constraints. '''

    if now is None: now = dt.time(dt.now())
    if starts is None and group is not None: starts = group['starts']
    if type(starts) is not list: starts = [starts]
    if ends is None and group is not None: ends = group['ends']
    if type(ends) is not list: ends = [ends]

    day_start = datetime.time(0, 0)
    day_end = datetime.time(23, 59)

    if starts == [] or ends == []:
        return True

    for i in range(len(starts)):
        if starts[i] < ends[i]:
            if now >= starts[i] and now <= ends[i]:
                return True
        else:
            if (now >= starts[i] and now <= day_end) or \
               (now <= ends[i]   and now >= day_start):
                return True

    return False

def block (filename, blocks):
    ''' main function to correct the hosts file. '''
    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    newdata = data[:]
    if type(blocks) is not list: blocks = [blocks]

    for group in blocks:
        if verbose:
            # print('group', group['name'], '(', group['start'], '->',
            #       group['end'], '):')
            print('group', group['name'], ':')
        if within_time(group=group):
            # construct lines of new file
            blockentries = [ '0.0.0.0\t'+i+'\n' for i in group['list'] ]
            for entry in blockentries:
                if entry not in data:
                    if '#'+entry in data:
                        # uncomment the line
                        if verbose:
                            print('\t', entry[:-1], 'is commented at line',
                            data.index('#'+entry))
                        newdata[data.index('#'+entry)] = entry
                    else:
                        # add the line
                        if verbose: print('\t', entry[:-1], 'is missing')
                        newdata.append(entry)
        elif verbose:
            print('\t not in time range')#, group['start'], '->', group['end'])

    if data == newdata:
        # file has not changed - don't bother writing
        if verbose: print('-- nothing\'s changed!')
    else:
        # update the file
        with open(filename, 'w') as f:
            f.writelines(newdata)
        if verbose: print('-- blocked')

def unblock (filename, blocks):
    ''' unblock all websites in the blocks, applied one-by-one. to be used after
    a schedule finishes.
    '''
    # get the data from the file
    with open(filename, 'r') as f:
        data = f.readlines()

    newdata = data[:]
    if type(blocks) is not list: blocks = [blocks]

    for group in blocks:
        if verbose: print('unblocking group', group['name']+':')

        # construct lines of new file
        blockentries = [ '#0.0.0.0\t'+i+'\n' for i in group['list'] ]
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
        if verbose: print('-- nothing\'s changed!')
    else:
        # update the file
        with open(filename, 'w') as f:
            f.writelines(newdata)
        if verbose: print('-- unblocked')
