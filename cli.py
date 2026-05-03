#!/usr/bin/env python3

import argparse
import atexit
import functools
import logging
import os
from pathlib import Path
import socket
import sys

import blockfile
import colour
from blockgroup import BlockGroup
import util


COULD_NOT_READ_RUNTIME_INFO_ATTR: str = "_cli_could_not_read_runtime_info"


def could_read_runtime_info(group: BlockGroup) -> bool:
    """ Were we able to read runtime info from the running service for this group? """
    return not hasattr(group, COULD_NOT_READ_RUNTIME_INFO_ATTR)


def mark_could_not_read_runtime_info(group: BlockGroup) -> None:
    """ Mark that we could not read runtime info from the running service for this
    group. If done, later calls to ``could_read_runtime_info`` on ``group`` will return
    ``False``.

    (Marking is done by injecting an extra property on the ``BlockGroup``.)

    """
    setattr(group, COULD_NOT_READ_RUNTIME_INFO_ATTR, True)


def send_message(*args: str) -> None:
    """ Send a message to the running service. Will error if the service isn't running.
    """
    with socket.socket() as s:
        s.connect(("0.0.0.0", util.NETWORK_PORT))
        s.sendall(util.msg_segments(*args))


def request_data(*args: str) -> list[str]:
    """ Request some data from the running service, and wait to receive a response
    before returning it. Will error if the service isn't running.
    """
    response = ""

    with socket.socket() as s:
        s.connect(("0.0.0.0", util.NETWORK_PORT))
        s.sendall(util.msg_segments("request", *args))

        # Try to read until we've got a full message.
        response = b""
        while not response.endswith(util.MSG_SEPARATOR.encode()):
            if not (new_data := s.recv(util.SOCKET_RECV_BUFSIZE)):
                break
            response += new_data

        response = response.decode().strip().split(util.MSG_SEGMENT_SEPARATOR)
        assert response[0] == "response"
        return response[1:]


@functools.cache
def groups (bf_path: Path | None = None, fail_on_connection_refused: bool = True) -> list[BlockGroup]:
    """
    Get all the block groups from a detected standard blockfile location, in the order
    in which they appear in the file.

    :param bf_path: Location of blockfile (else pick a standard default).
    """
    if bf_path is None:
        bf_path = blockfile.get_filename()
    res = blockfile.read(bf_path)

    # For groups with duration constraints, request their paused state from the service.
    for group in res:
        if group.duration is None:
            continue
        try:
            response = request_data("is_paused", group.canonical_name())
            assert response[0] == group.canonical_name()
            group.is_paused = response[1] == "true"
        except ConnectionRefusedError as e:
            if fail_on_connection_refused:
                raise e
            mark_could_not_read_runtime_info(group)

    return res


def maybe_coloured_group_name (group: BlockGroup, should_colour: bool = True,
                               prefix: str = "", suffix: str = "") -> str:
    """
    Get the name of the given ``group``, suitably coloured based on state &
    ``should_colour`` option.
    """
    ret = group.display_name()
    if should_colour:
        if not group.is_blocking():
            ret = colour.grey(ret)

        if not could_read_runtime_info(group):
            ret = ret + colour.yellow(" (paused status unknown)")
        elif group.is_paused:
            ret = colour.yellow("(paused) ") + ret

        remaining = group.duration_summary()
        if remaining is not None:
            remaining = f" ({remaining})"
            if should_colour:
                c = colour.red if group.duration_remaining().total_seconds() <= 0 else colour.cyan
                remaining = c(remaining)
            ret += remaining
    return prefix + ret + suffix


def ls (blocked_filter: bool | None = None,
        bf_path: Path | None = None,
        should_colour: bool = True) -> None:
    """
    Command: list block groups.

    :param blocked_filter: Filters groups: if ``True``, will list only the currently
                           active groups; if ``False``, only the inactive ones; if
                           ``None``, will list all groups.
    :param bf_path: Location of blockfile (else pick a standard default).
    """
    names: list[str] = []
    gs = groups(bf_path=bf_path, fail_on_connection_refused=False)
    if any(not could_read_runtime_info(g) for g in gs):
        logging.warning(f"{colour.yellow('WARNING')}: Couldn't connect to service (are "
                        "you sure it's running?); will not be able to get runtime "
                        "status of groups.")
    for g in gs:
        if blocked_filter == True and g.is_blocking():
            print(maybe_coloured_group_name(g, should_colour))
        elif blocked_filter == False and not g.is_blocking():
            print(maybe_coloured_group_name(g, should_colour))
        elif blocked_filter is None:
            print(maybe_coloured_group_name(g, should_colour))


def show (group_name: str,
          bf_path: Path | None = None,
          should_colour: bool = True) -> None:
    """
    Command: show information about a particular block group.

    :param group_name: (Prefix of) name of the group to show.
    :param bf_path: Location of blockfile (else pick a standard default).
    """
    gs = groups(bf_path=bf_path, fail_on_connection_refused=False)
    to_show: BlockGroup = get_prefix_group_match(group_name, gs)

    if not could_read_runtime_info(to_show):
        logging.warning(f"{colour.yellow('WARNING')}: Couldn't connect to service (are "
                        "you sure it's running?); will not be able to get runtime "
                        "status of groups.")
    print(maybe_coloured_group_name(to_show, should_colour, suffix=":\n"))
    print(to_show)


def get_prefix_group_match (name_prefix: str, groups: list[BlockGroup]) -> BlockGroup:
    """ Like ``utils.get_unique_prefix_match``, but for group names; return the matching
    ``BlockGroup`` itself.
    """
    try:
        group_name = util.get_unique_prefix_match(name_prefix, [g.name for g in groups])
    except ValueError as e:
        logging.error(f"{colour.red('ERROR')}: {e}")
        sys.exit(1)
    # Note: get_unique_prefix_match will handle ambiguous match
    return next(g for g in groups if g.name == group_name)


def set_paused (group_name: str, paused: bool, bf_path: Path | None = None) -> None:
    """ Either pause or unpause a block group, if it's one with a duration-based block.
    """
    to_pause: BlockGroup = get_prefix_group_match(group_name, groups(bf_path=bf_path))

    if to_pause.duration is None:
        logging.warning("Can only pause block groups with duration constraints, but "
                        f"'{colour.cyan(str(to_pause.display_name()))}' doesn't have "
                        "any.")
        return

    send_message("set_paused", to_pause.canonical_name(), str(paused).lower())

    to_pause.is_paused = paused

    # try and get more up-to-date state, after waiting a bit for messages to go through
    _ = request_data("is_paused", to_pause.canonical_name())
    to_pause.load_state()

    logging.warning(maybe_coloured_group_name(to_pause, True))


def pause (group_name: str, bf_path: Path | None = None) -> None:
    """ Command: pause a block group, if it's one with a duration-based block. """
    return set_paused(group_name, True, bf_path)


def unpause (group_name: str, bf_path: Path | None = None) -> None:
    """ Command: unpause a block group, if it's one with a duration-based block. """
    return set_paused(group_name, False, bf_path)


def main ():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    # This is just a funny little hack to allow specifying arguments for multiple
    # subparsers just once.
    common_args_parser = argparse.ArgumentParser(add_help=False)
    common_args_parser.add_argument(
        "--blockfile", "-f",
        required=False,
        default=None,
        help="Path to block file (else will assume a default)")
    common_args_parser.add_argument(
        "--colours",  # can't see any short option support from BooleanOptionalAction :(
        action=argparse.BooleanOptionalAction,
        help=("Should output be coloured? If not set, will choose based on whether "
              "terminal is interactive"),
    )
    common_args_parser.add_argument('-v', '--verbose',
                                    action='store_true',
                                    help=('Whether to log some extra messages to '
                                          'stdout.'))

    parser_list = subparsers.add_parser(
        "list",
        parents=[common_args_parser],
        help="List block groups")
    blocked_filter_group = parser_list.add_mutually_exclusive_group()
    blocked_filter_group.add_argument(
        "--blocked", "-b",
        action="store_true",
        help="List only groups currently being blocked (exclusive with --unblocked")
    blocked_filter_group.add_argument(
        "--unblocked", "-u",
        action="store_true",
        help="List only groups currently being blocked (exclusive with --blocked")

    parser_show = subparsers.add_parser(
        "show",
        parents=[common_args_parser],
        help="Show information on a particular block group")
    parser_show.add_argument(
        "show_block_group",
        help="Name of the block group to show.")

    parser_pause = subparsers.add_parser(
        "pause",
        parents=[common_args_parser],
        help="Pause the given block group, if allowed.")
    parser_pause.add_argument(
        "pause_block_group",
        help="Name of the block group to pause.")

    parser_unpause = subparsers.add_parser(
        "unpause",
        parents=[common_args_parser],
        help="Unpause the given block group, if allowed.")
    parser_unpause.add_argument(
        "unpause_block_group",
        help="Name of the block group to unpause.")

    args: argparse.Namespace = parser.parse_args()

    if args.command is None:
        # if we weren't given a command, then `args` won't have properties for the
        # common arguments to the next parsing step will fail.
        print("Please provide a command, or -h/--help to print help.",
              file=sys.stderr)
        return

    logging.basicConfig(format='%(message)s',
                        level='NOTSET' if args.verbose else 'WARNING')

    # parse general args
    should_colour = args.colours
    if should_colour is None:
        should_colour = os.isatty(sys.stdout.fileno())

    bf_path = args.blockfile
    if bf_path is not None:
        bf_path = Path(bf_path)

    try:
        # parse subcommands
        match args.command:
            case 'pause':
                pause(args.pause_block_group, bf_path)
            case 'unpause':
                unpause(args.unpause_block_group, bf_path)
            case 'list':
                blocked_filter: bool | None = None
                if args.blocked:
                    blocked_filter = True
                if args.unblocked:
                    blocked_filter = False

                ls(blocked_filter, bf_path, should_colour)
            case 'show':
                show(args.show_block_group)
            case _:
                raise NotImplementedError(f"Unhandled command {args.command}.")
    except ConnectionRefusedError:
        logging.error(f"{colour.red('ERROR')}: connection to service refused. Are you "
                      "sure the service is running?")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
        sys.stdout.flush()
    except BrokenPipeError:
        # python flushes standard streams on exit; redirect remaining output to
        # /dev/null to avoid another BrokenPipeError at shutdown.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())