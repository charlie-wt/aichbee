#!/usr/bin/env python3

import sys
import datetime

from datetime import datetime as dt
from inotify_simple import INotify, flags

import blockfile as bf
from blocktime import Time, within_time
import refresh as rf


'''
A very simple program to set time limits on websites.

'''

def main ():
    timeout_ms = 30000

    num_args = len(sys.argv)
    bf.verbose = False
    rf.verbose = False
    verbose = False

    # file to watch (default /etc/hosts)
    target = '/etc/hosts'
    if num_args >= 2: target = sys.argv[1]
    ref_dir  = target[:target.rfind('/')+1]
    ref_file = target[target.rfind('/')+1:]

    # location of blocklist file (default ./blocklist)
    blocks = None
    if num_args >= 3:
        blocks = bf.read(sys.argv[2])
    else:
        blocks = bf.read('./blocklist')
    if verbose: print(blocks)

    # configure inotify
    inotify = INotify()
    watch_flags = flags.MODIFY
    wd = inotify.add_watch(ref_dir, watch_flags)

    prevtime = Time.now()
    # TODO #performance: not particularly efficient
    for group in blocks:
        if group.within_time():
            rf.block(target, group)
        else:
            rf.unblock(target, group)

    # read events, maybe respond
    while True:
        # check for the start of a group's time constrains
        now = Time.now()
        for group in blocks:
            if not group.within_time(now=prevtime) and group.within_time(now=now):
                if verbose: print('time start for group', group.name)
                rf.block(target, group)
            if group.within_time(now=prevtime) and not group.within_time(now=now):
                if verbose: print('time end for group', group.name)
                rf.unblock(target, group)

        prevtime = now
        # check for file modification events
        for event in inotify.read(timeout=timeout_ms):
            if event[3] == ref_file:
                rf.block(target, blocks)

if __name__ == '__main__':
    main()
