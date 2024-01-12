#!/usr/bin/env python3

import argparse
from datetime import datetime as dt
from inotify_simple import INotify, flags
import os

import blockfile as bf
from blocktime import Time, within_constraints
import refresh as rf


'''
A very simple program to set time constraints on websites.

'''


verbose = True


def log (*args, **kwargs):
    if verbose: print(*args, **kwargs)


def parse_args ():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target',
                        default=os.path.abspath(os.path.join(os.path.sep, 'etc', 'hosts')),
                        help='Path to hosts file to manage.')
    parser.add_argument('-b', '--blocklist',
                        default=bf.get_filename(),
                        help='Path to blocklist to enforce.')
    return parser.parse_args()


def main ():
    timeout_ms = 30000

    bf.verbose = False
    rf.verbose = True

    args = parse_args()

    # file to watch
    args.target = os.path.abspath(args.target)
    log(f'watching {args.target}')
    target_dir, target_file = os.path.split(args.target)

    # location of blocklist file
    log(f'getting blocklist from {args.blocklist}')
    blocks = bf.read(args.blocklist)
    for b in blocks: log(b)

    # configure inotify
    inotify = INotify()
    watch_flags = flags.MODIFY
    wd = inotify.add_watch(target_dir, watch_flags)

    prevtime = Time.now()
    # TODO #performance: not particularly efficient
    for group in blocks:
        if group.within_constraints():
            rf.block(args.target, group)
        else:
            rf.unblock(args.target, group)

    # read events, maybe respond
    while True:
        # check for the start of a group's time constrains
        now = Time.now()
        for group in blocks:
            if not group.within_constraints(prevtime) and group.within_constraints(now):
                log(f'time start for group {group.display_name()}')
                rf.block(args.target, group)
            if group.within_constraints(prevtime) and not group.within_constraints(now):
                log(f'time end for group {group.display_name()}')
                rf.unblock(args.target, group)

        prevtime = now
        # check for file modification events
        for event in inotify.read(timeout=timeout_ms):
            if event[3] == target_file:
                rf.block(args.target, blocks)

if __name__ == '__main__':
    main()
