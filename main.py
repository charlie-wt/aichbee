#!/usr/bin/env python3

import argparse
from contextlib import contextmanager
from datetime import datetime as dt
from inotify_simple import INotify, flags
import logging
import os

import blockfile as bf
from blocktime import Time, within_constraints
import refresh as rf


'''
A very simple program to set time constraints on websites.

'''


def parse_args ():
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--watchfile',
                        default=os.path.abspath(os.path.join(os.path.sep, 'etc', 'hosts')),
                        help='Path to file to watch & manage (eg. hosts).')
    parser.add_argument('-b', '--blocklist',
                        default=bf.get_filename(),
                        help='Path to blocklist to enforce.')
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Whether to log some extra messages to stdout.')
    return parser.parse_args()


def main ():
    timeout_ms = 30000

    args = parse_args()

    # set up logging
    logging.basicConfig(format='%(message)s',
                        level='NOTSET' if args.verbose else 'WARNING')

    # file to watch
    args.watchfile = os.path.abspath(args.watchfile)
    logging.debug(f'watching {args.watchfile}')
    watchfile_dir, watchfile_name = os.path.split(args.watchfile)

    # location of blocklist file
    logging.debug(f'getting blocklist from {args.blocklist}')
    blocks = bf.read(args.blocklist)
    for b in blocks: logging.debug(b)

    # do an initial refresh
    prevtime = Time.now()
    # TODO #performance: not particularly efficient
    for group in blocks:
        if group.within_constraints():
            rf.block(args.watchfile, group)
        else:
            rf.unblock(args.watchfile, group)

    # configure inotify
    inotify = INotify()
    wd = inotify.add_watch(watchfile_dir, flags.MODIFY)
    @contextmanager
    def suspend_watch():
        nonlocal wd
        try:
            inotify.rm_watch(wd)
            yield None
        finally:
            wd = inotify.add_watch(watchfile_dir, flags.MODIFY)

    # read events, maybe respond
    while True:
        print('=== checking whether to refresh watched file ==========================')

        # check for the start of a group's time constrains
        now = Time.now()
        for group in blocks:
            if not group.within_constraints(prevtime) and group.within_constraints(now):
                logging.debug(f'time start for group {group.display_name()}')
                with suspend_watch():
                    rf.block(args.watchfile, group)
            if group.within_constraints(prevtime) and not group.within_constraints(now):
                logging.debug(f'time end for group {group.display_name()}')
                with suspend_watch():
                    rf.unblock(args.watchfile, group)

        prevtime = now
        # check for file modification events
        for event in inotify.read(timeout=timeout_ms):
            if event.name == watchfile_name and group.within_constraints(now):
                logging.debug("watched file was edited!")
                with suspend_watch():
                    rf.block(args.watchfile, blocks)

if __name__ == '__main__':
    main()
