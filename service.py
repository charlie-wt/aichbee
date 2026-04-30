#!/usr/bin/env python3

import argparse
import asyncio
from contextlib import contextmanager
from datetime import datetime as dt
# from inotify_simple import INotify, flags
import logging
import os
from pathlib import Path

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


import sys
def main ():
    timeout_ms = 30000

    args = parse_args()

    # set up logging
    logging.basicConfig(format='%(message)s',
                        level='NOTSET' if args.verbose else 'WARNING')

    # file to watch
    args.watchfile = os.path.abspath(args.watchfile)
    logging.debug(f'watching {args.watchfile}')
    # watchfile_dir, watchfile_name = os.path.split(args.watchfile)

    # location of blockfile
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

    prevtime = dt.now()

    # TODO #temp
    for b in blocks:
        if b.duration is not None:
            b.update_state(prevtime)

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

    watchfile_lock = asyncio.Lock()

    watchfile_poll_rate_seconds: float = 1
    watchfile_prev_modified_time: float = os.stat(args.watchfile).st_mtime

    async def locked_refresh():
        nonlocal watchfile_prev_modified_time
        async with watchfile_lock:
            full_refresh()
            watchfile_prev_modified_time = os.stat(args.watchfile).st_mtime

    async def watch_watchfile_for_changes():
        nonlocal watchfile_prev_modified_time
        watchfile_prev_modified_time = os.stat(args.watchfile).st_mtime

        while True:
            await asyncio.sleep(watchfile_poll_rate_seconds)

            new_time: float = os.stat(args.watchfile).st_mtime
            if new_time != watchfile_prev_modified_time:
                logging.debug("watchfile changed!")
                await locked_refresh()

    async def wait_for_next_schedule_boundary():
        now = dt.now()

        next_changes = [group.next_schedule_change(now) for group in blocks]
        next_changes = [c for c in next_changes if c is not None]
        next_boundary: dt = min(next_changes)

        logging.debug(f"next schedule constraint boundary at {next_boundary}")

        await asyncio.sleep((next_boundary - now).total_seconds())

    async def schedule_coro():
        while True:
            await asyncio.create_task(wait_for_next_schedule_boundary())

            logging.debug("refreshing from schedule!")
            await locked_refresh()

    loop = asyncio.new_event_loop()
    asyncio.ensure_future(schedule_coro(), loop=loop)
    asyncio.ensure_future(watch_watchfile_for_changes(), loop=loop)

    try:
        # run the event loop. hit ctrl-c to stop.
        loop.run_forever()
    except KeyboardInterrupt:
        print("Stopping")
    finally:
        # done; try to close the event loop cleanly.
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # run the loop briefly to allow cancelled tasks to finish their cleanup.
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()



if __name__ == '__main__':
    main()
