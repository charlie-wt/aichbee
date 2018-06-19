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
    verbose = True

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

    prevtime = dt.time(dt.now())
    # TODO #performance: not particularly efficient
    for group in blocks:
        if rf.within_time(group=group, now=prevtime):
            rf.block(target, group)
        else:
            rf.unblock(target, group)
    # read events, maybe respond
    while True:
        # check for the start of a group's time constrains
        now = dt.time(dt.now())
        for group in blocks:
            if not rf.within_time(group=group, now=prevtime) and \
               rf.within_time(group=group, now=now):
                if verbose:
                    print('time start for group', group['name'])
                rf.block(target, group)
            if rf.within_time(group=group, now=prevtime) and \
               not rf.within_time(group=group, now=now):
                if verbose:
                    print('time end for group', group['name'])
                rf.unblock(target, group)
        prevtime = now
        # check for file modification events
        for event in inotify.read(timeout=30000):
            if event[3] == ref_file:
                rf.block(target, blocks)

if __name__ == '__main__':
    main()
