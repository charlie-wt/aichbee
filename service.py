#!/usr/bin/env python3

import argparse
import asyncio
from contextlib import contextmanager
from datetime import datetime as dt
import functools
# from inotify_simple import INotify, flags
import logging
import os
from pathlib import Path
import signal

import blockfile as bf
from blocktime import Time, within_constraints
import refresh as rf
import util


'''
A very simple program to set time constraints on websites.

'''


WATCHFILE_POLL_RATE_SECONDS: float = 1


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


import sys
def main ():
    # timeout_ms = 30000

    args = parse_args()

    # setup
    logging.basicConfig(format='%(message)s',
                        level='NOTSET' if args.verbose else 'WARNING')

    args.watchfile = os.path.abspath(args.watchfile)
    logging.debug(f'watching {args.watchfile}')
    # watchfile_dir, watchfile_name = os.path.split(args.watchfile)

    logging.debug(f'getting blockfile from {args.blockfile}')
    blocks: list[BlockGroup] = bf.read(args.blockfile)
    for b in blocks: logging.debug(b)

    def full_refresh():
        for group in blocks:
            if group.is_blocking():
                rf.block(args.watchfile, group)
            else:
                rf.unblock(args.watchfile, group)

    # do an initial refresh
    full_refresh()

    start_time = dt.now()
    # TODO #temp
    for b in blocks:
        if b.duration is not None:
            b.update_state(start_time)

    # # configure inotify
    # inotify = INotify()
    # watchfile_watch_descriptor: int = inotify.add_watch(watchfile_dir, flags.MODIFY)
    # # state_watch_descriptor: int = inotify.add_watch(util.state_dir(), flags.MODIFY)

    # @contextmanager
    # def suspend_watch():
    #     nonlocal watchfile_watch_descriptor
    #     nonlocal state_watch_descriptor
    #     try:
    #         inotify.rm_watch(watchfile_watch_descriptor)
    #         # inotify.rm_watch(state_watch_descriptor)
    #         yield None
    #     finally:
    #         watchfile_watch_descriptor = inotify.add_watch(watchfile_dir, flags.MODIFY)
    #         # state_watch_descriptor = inotify.add_watch(util.state_dir(), flags.MODIFY)

    # define event loop tasks
    watchfile_prev_modified_time: float = os.stat(args.watchfile).st_mtime
    watchfile_lock = asyncio.Lock()

    async def locked_refresh():
        nonlocal watchfile_prev_modified_time
        async with watchfile_lock:
            full_refresh()
            watchfile_prev_modified_time = os.stat(args.watchfile).st_mtime

    async def watch_watchfile_for_changes():
        nonlocal watchfile_prev_modified_time
        watchfile_prev_modified_time = os.stat(args.watchfile).st_mtime

        while True:
            await asyncio.sleep(WATCHFILE_POLL_RATE_SECONDS)

            new_time: float = os.stat(args.watchfile).st_mtime
            if new_time != watchfile_prev_modified_time:
                logging.debug("watchfile changed!")
                await locked_refresh()

    async def refresh_on_schedule():
        while True:
            now = dt.now()

            next_changes = [group.next_schedule_change(now) for group in blocks]
            next_changes = [c for c in next_changes if c is not None]
            next_boundary: dt = min(next_changes)
            logging.debug(f"next schedule constraint boundary at {next_boundary}")

            await asyncio.sleep((next_boundary - now).total_seconds())

            logging.debug("refreshing from schedule!")
            await locked_refresh()

    # start event loop
    loop = asyncio.new_event_loop()
    asyncio.ensure_future(refresh_on_schedule(), loop=loop)
    asyncio.ensure_future(watch_watchfile_for_changes(), loop=loop)

    # handle signals to stop cleanly
    if hasattr(signal, 'SIGINT'):
        loop.add_signal_handler(signal.SIGINT, loop.stop)
    if hasattr(signal, 'SIGTERM'):
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

    try:
        # run the event loop. hit ctrl-c to stop.
        loop.run_forever()
    finally:
        # cleanup
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # run the loop briefly to allow cancelled tasks to finish their cleanup.
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


if __name__ == '__main__':
    main()
