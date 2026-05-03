#!/usr/bin/env python3

import argparse
import asyncio
from contextlib import contextmanager
from datetime import datetime as dt
import functools
import logging
import os
from pathlib import Path
import signal

import blockfile
from blockgroup import BlockGroup
import refresh
import util


'''
A very simple program to set time constraints on websites.

'''


WATCHFILE_POLL_RATE_SECONDS: float = 1
DURATION_UPDATE_RATE_SECONDS: float = 1


def parse_args ():
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--watchfile',
                        default=os.path.abspath(os.path.join(os.path.sep, 'etc', 'hosts')),
                        help='Path to file to watch & manage (eg. hosts).')
    parser.add_argument('-b', '--blockfile',
                        default=str(blockfile.get_filename()),
                        help='Path to blockfile to enforce.')
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Whether to log some extra messages to stdout.')
    return parser.parse_args()


def main ():
    args = parse_args()

    # setup.
    logging.basicConfig(format='%(message)s',
                        level='NOTSET' if args.verbose else 'WARNING')

    args.watchfile = os.path.abspath(args.watchfile)
    logging.debug(f'watching {args.watchfile}')

    args.blockfile = str(Path(args.blockfile).resolve())
    logging.debug(f'getting blockfile from {args.blockfile}')
    blocks: list[BlockGroup] = blockfile.read(args.blockfile)
    for b in blocks: logging.debug(b)

    def refresh_watchfile_from_groups(groups: list[BlockGroup] | None = None):
        groups = groups or blocks
        for group in groups:
            if group.is_blocking():
                refresh.block(args.watchfile, group)
            else:
                refresh.unblock(args.watchfile, group)

    refresh_watchfile_from_groups()

    start_time = dt.now()
    for b in blocks:
        if b.duration is not None:
            b.update_state(start_time)

    # define event loop tasks.
    watchfile_prev_modified_time: float = os.stat(args.watchfile).st_mtime
    watchfile_lock = asyncio.Lock()

    async def locked_refresh_from_groups(groups: list[BlockGroup] | None = None):
        nonlocal watchfile_prev_modified_time
        async with watchfile_lock:
            refresh_watchfile_from_groups(groups)
            watchfile_prev_modified_time = os.stat(args.watchfile).st_mtime

    async def watch_watchfile_for_changes():
        nonlocal watchfile_prev_modified_time
        watchfile_prev_modified_time = os.stat(args.watchfile).st_mtime

        while True:
            await asyncio.sleep(WATCHFILE_POLL_RATE_SECONDS)

            new_time: float = os.stat(args.watchfile).st_mtime
            if new_time != watchfile_prev_modified_time:
                logging.debug("watchfile changed!")
                await locked_refresh_from_groups()

    async def refresh_on_schedule():
        while True:
            now = dt.now()

            # Get next group to cross a boundary in its schedule constraints, and when
            # that will be.
            next_group: BlockGroup | None = None
            next_boundary: dt | None = None
            for group in blocks:
                candidate_boundary: dt = group.next_schedule_change(now)
                if candidate_boundary is None:
                    continue
                if next_boundary is None or next_boundary > candidate_boundary:
                    next_group = group
                    next_boundary = candidate_boundary

            if next_group is None or next_boundary is None:
                continue
            logging.debug(f"next schedule constraint boundary at {next_boundary}")

            # Wait for the boundary, then refresh
            await asyncio.sleep((next_boundary - now).total_seconds())

            logging.debug("refreshing from schedule!")
            await locked_refresh_from_groups([next_group])

    was_blocking_last_time: dict[str, bool] = {}
    async def refresh_on_duration():
        while True:
            await asyncio.sleep(DURATION_UPDATE_RATE_SECONDS)

            changed: list[BlockGroup] = []

            any_changes: bool = False
            now = dt.now()
            for group in blocks:
                if group.duration is None:
                    continue

                group.update_state(now)
                is_blocking_now = group.is_blocking(now)

                # NOTE: constraint on blockfile parsing means all groups with a duration
                # constraint should have a name too.
                last_time = was_blocking_last_time.get(group.canonical_name())
                if last_time is not None and is_blocking_now != last_time:
                    changed.append(group)

                was_blocking_last_time[group.canonical_name()] = is_blocking_now

            if changed:
                await locked_refresh_from_groups(changed)

    def parse_group_name_from_message(full_group_name: str) -> BlockGroup | None:
        config_path, group_name = full_group_name.split("::", maxsplit=1)

        if args.blockfile != config_path:
            logging.warning("Running under a different config path to us")
            return None

        return next((g for g in blocks if g.name == group_name), None)

    async def receive_message(reader: asyncio.StreamReader,
                              writer: asyncio.StreamWriter,
                              message: list[str]):
        command, *args = message

        if command == "set_paused":
            if len(args) != 2:
                logging.error(
                    "Expected 2 args for 'set_paused' message (canonical group "
                    f"name + is_paused), but got {len(args)}"
                )
                return
            group: BlockGroup = parse_group_name_from_message(args[0])
            if group is None:
                logging.warning("Unknown group")
                return

            if group.duration is None:
                return

            if args[1] == "true":
                group.pause()
                await locked_refresh_from_groups([group])
            elif args[1] == "false":
                group.unpause()
                await locked_refresh_from_groups([group])
            else:
                logging.error(f"Failed to parse is_paused: {args[1]}")
        elif command == "request":
            if args[0] == "is_paused":
                group: BlockGroup = parse_group_name_from_message(args[1])
                if group is None:
                    logging.warning("Unknown group")
                    return

                response = ["response", args[1], str(group.is_paused).lower()]
                logging.debug(f"Sending response {response}")
                writer.write(util.msg_segments(*response))
                await writer.drain()
            else:
                writer.write(util.msg_segments("error", f"unknown request type {args[0]}"))
                await writer.drain()
        else:
            writer.write(util.msg_segments("error", f"unknown command {command}"))
            await writer.drain()

    async def client_connected(reader: asyncio.StreamReader,
                               writer: asyncio.StreamWriter):
        # Try to read until we've got a full message.
        data = b""
        while not data.endswith(util.MSG_SEPARATOR.encode()):
            new_data = await reader.read(util.SOCKET_RECV_BUFSIZE)
            if not new_data:  # empty bytes object => eof received
                break
            data += new_data

        messages = data.decode().strip().split(util.MSG_SEPARATOR)

        for msg in messages:
            lines = msg.strip().split(util.MSG_SEGMENT_SEPARATOR)
            logging.debug(f"Received message: {lines}")
            await receive_message(reader, writer, lines)

        writer.close()
        await writer.wait_closed()

    async def message_server():
        server = await asyncio.start_server(
            client_connected, "0.0.0.0", util.NETWORK_PORT)

        async with server:
            await server.serve_forever()

    # start event loop.
    loop = asyncio.new_event_loop()
    asyncio.ensure_future(refresh_on_schedule(), loop=loop)
    asyncio.ensure_future(refresh_on_duration(), loop=loop)
    asyncio.ensure_future(watch_watchfile_for_changes(), loop=loop)
    asyncio.ensure_future(message_server(), loop=loop)

    # handle signals to stop cleanly.
    if hasattr(signal, 'SIGINT'):
        loop.add_signal_handler(signal.SIGINT, loop.stop)
    if hasattr(signal, 'SIGTERM'):
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

    try:
        # run the event loop. hit ctrl-c to stop.
        loop.run_forever()
    finally:
        # cleanup.
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # run the loop briefly to allow cancelled tasks to finish their cleanup.
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


if __name__ == '__main__':
    main()
