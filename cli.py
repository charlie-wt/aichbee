#!/usr/bin/env python3

import argparse
import functools
import logging
import os
from pathlib import Path
import sys

import blockfile
import colour
from blockgroup import BlockGroup
import util


@functools.cache
def groups (bf_path: Path | None = None) -> list[BlockGroup]:
    """
    Get all the block groups from a detected standard blockfile location, in the order
    in which they appear in the file.

    :param bf_path: Location of blockfile (else pick a standard default).
    """
    if bf_path is None:
        bf_path = blockfile.get_filename()
    return blockfile.read(str(bf_path.resolve()))


def maybe_coloured_group_name (group: BlockGroup, should_colour: bool = True) -> str:
    """
    Get the name of the given ``group``, suitably coloured based on state &
    ``should_colour`` option.
    """
    ret = group.display_name()
    if should_colour:
        if not group.is_blocking():
            ret = colour.grey(ret)
        # TODO #temp
        if group.state.is_paused:
            ret = "* " + ret
    # TODO #enhancement: colouring for 'schedule-based constraint would be open, but
    # group is paused.'
    return ret


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
    for g in groups(bf_path=bf_path):
        if blocked_filter == True and g.is_blocking():
            print(maybe_coloured_group_name(g, should_colour))
        elif blocked_filter == False and not g.is_blocking():
            print(maybe_coloured_group_name(g, should_colour))
        elif blocked_filter is None:
            print(maybe_coloured_group_name(g, should_colour))


# TODO #enhancement: either disallow duplicate group names earlier, or add an extra
# interactive step to select a group based on a preview of its contents.
def get_prefix_group_match (name_prefix: str, groups: list[BlockGroup]) -> BlockGroup:
    """ Like ``utils.get_unique_prefix_match``, but for group names; return the matching
    ``BlockGroup`` itself.
    """
    group_name = util.get_unique_prefix_match(name_prefix, [g.name for g in groups])
    # Note: get_unique_prefix_match will handle ambiguous match
    return next(g for g in groups if g.name == group_name)


# TODO #correctness: return whether the group is now open?
def set_paused (group_name: str, paused: bool, bf_path: Path | None = None) -> None:
    """ Either pause or unpause a block group, if it's one with a duration-based block.
    """
    to_pause: BlockGroup = get_prefix_group_match(group_name, groups(bf_path=bf_path))
    # TODO #robustness: communicating 'pausedness' via a file like this, which is also
    # being written to periodically by the service (to update things like duration
    # remaining), introduces a potential race condition.
    #
    # i don't think there's a way to have the pausedness persist across reboots without
    # writing to a file like this (which also acts as a convenient method of ipc). it
    # might not be too bad ux if we just re-pause anything pausable on shutdown, though.
    # similarly, prob can't have updating-duration-across-reboots-correctly work simply
    # without something regularly writing a `duration_remaining` value back to a file.
    # that has to be the service, since it's the only thing running over time.
    #
    # could have separate files for pausedness & `duration_remaining`, since pausedness
    # will only be written by cli & `duration_remaining` will only be written by the
    # service.
    if paused:
        to_pause.pause()
    else:
        to_pause.unpause()
    logging.info(f'{"" if paused else "un"}paused {to_pause.display_name()}')


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
        case _:
            raise NotImplementedError(f"Unhandled command {args.command}.")


if __name__ == '__main__':
    try:
        main()
        sys.stdout.flush()
    except BrokenPipeError:
        # python flushes standard streams on exit; redirect remaining output to
        # /dev/null to avoid another BrokenPipeError at shutdown.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())