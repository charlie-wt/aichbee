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


def arg_or (idx: int, default: str) -> str:
    return sys.argv[idx] if idx < len(sys.argv) else default


def main ():
    timeout_ms = 30000

    bf.verbose = False
    rf.verbose = False
    verbose = False

    # file to watch
    target_fname = arg_or(1, '/etc/hosts')
    if verbose: print(f'watching {target_fname}')

    ref_dir  = target_fname[:target_fname.rfind('/')+1]
    ref_file = target_fname[target_fname.rfind('/')+1:]

    # location of blocklist file
    blocklist_fname = arg_or(2, bf.get_filename())
    if verbose: print(f'getting blocklist from {blocklist_fname}')

    blocks = bf.read(blocklist_fname)
    if verbose: print(blocks)

    # configure inotify
    inotify = INotify()
    watch_flags = flags.MODIFY
    wd = inotify.add_watch(ref_dir, watch_flags)

    prevtime = Time.now()
    # TODO #performance: not particularly efficient
    for group in blocks:
        if group.within_time():
            rf.block(target_fname, group)
        else:
            rf.unblock(target_fname, group)

    # read events, maybe respond
    while True:
        # check for the start of a group's time constrains
        now = Time.now()
        for group in blocks:
            if not group.within_time(now=prevtime) and group.within_time(now=now):
                if verbose: print('time start for group', group.name)
                rf.block(target_fname, group)
            if group.within_time(now=prevtime) and not group.within_time(now=now):
                if verbose: print('time end for group', group.name)
                rf.unblock(target_fname, group)

        prevtime = now
        # check for file modification events
        for event in inotify.read(timeout=timeout_ms):
            if event[3] == ref_file:
                rf.block(target_fname, blocks)

if __name__ == '__main__':
    main()
