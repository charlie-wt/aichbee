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
import util


'''
A very simple program to set time constraints on websites.

'''


def parse_args ():
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--watchfile',
                        default=os.path.abspath(os.path.join(os.path.sep, 'etc', 'hosts')),
                        help='Path to file to watch & manage (eg. hosts).')
    parser.add_argument('-b', '--blockfile',
                        default=str(bf.get_filename()),
                        help='Path to blockfile to enforce.')
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

    # location of blockfile
    logging.debug(f'getting blockfile from {args.blockfile}')
    blocks: list[BlockGroup] = bf.read(args.blockfile)
    for b in blocks: logging.debug(b)

    # do an initial refresh
    prevtime = dt.now()
    # TODO #performance: not particularly efficient
    for group in blocks:
        if group.is_blocking():
            rf.block(args.watchfile, group)
        else:
            rf.unblock(args.watchfile, group)

    # TODO #temp
    for b in blocks:
        if b.duration is not None:
            b.update_state(prevtime)

    # configure inotify
    inotify = INotify()
    watchfile_watch_descriptor: int = inotify.add_watch(watchfile_dir, flags.MODIFY)
    state_watch_descriptor: int = inotify.add_watch(util.state_dir(), flags.MODIFY)

    @contextmanager
    def suspend_watch():
        nonlocal watchfile_watch_descriptor
        nonlocal state_watch_descriptor
        try:
            inotify.rm_watch(watchfile_watch_descriptor)
            inotify.rm_watch(state_watch_descriptor)
            yield None
        finally:
            watchfile_watch_descriptor = inotify.add_watch(watchfile_dir, flags.MODIFY)
            state_watch_descriptor = inotify.add_watch(util.state_dir(), flags.MODIFY)

    while True:
        print('=== checking whether to refresh watched file ==========================')

        # check for the start of a group's time constrains
        now = dt.now()
        for group in blocks:
            if not group.is_blocking(prevtime) and group.is_blocking(now):
                logging.debug(f'time start for group {group.display_name()}')
                with suspend_watch():
                    rf.block(args.watchfile, group)
            if group.is_blocking(prevtime) and not group.is_blocking(now):
                logging.debug(f'time end for group {group.display_name()}')
                with suspend_watch():
                    rf.unblock(args.watchfile, group)

        prevtime = now
        # check for file modification events
        for event in inotify.read(timeout=timeout_ms):
            if event.wd == watchfile_watch_descriptor:
                if event.name == watchfile_name:
                    # changed watchfile (just reaffirm blocks)
                    logging.debug("watched file was edited!")
                    with suspend_watch():
                        rf.block(args.watchfile, blocks)
            elif event.wd == state_watch_descriptor:
                # changed state (could be cli (un)pausing a group)
                for group in blocks:
                    if group.state_filename() == event.name:
                        logging.debug(f'state of {group.display_name()} changed')
                        with suspend_watch():
                            group.load_state()
                            if group.is_blocking():
                                rf.block(args.watchfile, group)
                            else:
                                rf.unblock(args.watchfile, group)

            # TODO #bug
            # with suspend_watch():
            #     for group in blocks:
            #         group.update_state()

if __name__ == '__main__':
    main()
