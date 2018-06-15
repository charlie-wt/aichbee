#!/usr/bin/env python3

import sys
import datetime
from datetime import datetime as dt
from inotify_simple import INotify, flags
import blockfile as bf
import refresh as rf

def main ():
    num_args = len(sys.argv)
    bf.verbose = True
    rf.verbose = True

    # file to watch (default /etc/hosts)
    target = '/etc/hosts'
    if num_args >= 2: target = sys.argv[1]
    ref_dir  = target[:target.rfind('/')+1]
    ref_file = target[target.rfind('/')+1:]

    # location of blocklist file (default ./blocklist.txt)
    blocks = None
    if num_args >= 3:
        blocks = bf.read(sys.argv[2])
    else:
        blocks = bf.read('./blocklist')

    # configure inotify
    inotify = INotify()
    watch_flags = flags.MODIFY
    wd = inotify.add_watch(ref_dir, watch_flags)

    # read events, maybe respond
    # TODO #performance: using infinite loop. could see if I could use events, and would that be better?
    prevtime = dt.time(dt.now())
    while True:
        # check for the start of a group's time constrains
        now = dt.time(dt.now())
        print('checking now (', now, ') against:')
        for group in blocks:
            print('\t', group['name'], ':', group['start'], '->', group['end'])
            if prevtime < group['start'] and now > group['start']:
                print('\t\t time start for group', group['name'])
                rf.refresh(target, group)
            if prevtime < group['end'] and now > group['end']:
                print('\t\t time end for group', group['name'])
                rf.unblock(target, group)
        prevtime = now
        # check for file modification events
        for event in inotify.read():
            if event[3] == ref_file:
                rf.refresh(target, blocks)

if __name__ == '__main__':
    main()
