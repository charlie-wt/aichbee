#!/usr/bin/env python3

import argparse
import functools
import os
from pathlib import Path
import sys

import blockfile
import colour
from blockgroup import BlockGroup


@functools.cache
def groups (bf_path: Path | None = None) -> list[BlockGroup]:
    """
    Get all the block groups from a detected standard blockfile location, in the order
    in which they appear in the file.

    :param bf_path: Location of blockfile (else pick a standard default).
    """
    if bf_path is None:
        bf_path = Path(blockfile.get_filename())
    return blockfile.read(str(bf_path.resolve()))


def maybe_coloured_group_name (group: BlockGroup, should_colour: bool = True) -> str:
    """
    Get the name of the given ``group``, suitably coloured based on state &
    ``should_colour`` option.
    """
    ret = group.name
    if should_colour:
        if not group.within_constraints():
            ret = colour.grey(ret)
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
        if blocked_filter == True and g.within_constraints():
            print(maybe_coloured_group_name(g, should_colour))
        elif blocked_filter == False and not g.within_constraints():
            print(maybe_coloured_group_name(g, should_colour))
        elif blocked_filter is None:
            print(maybe_coloured_group_name(g, should_colour))


def pause (group_name: str, bf_path: Path | None = None) -> None:
    """ Command: pause a block group, if it's one with a duration-based block. """
    matching = [ g for g in groups(bf_path=bf_path) if g.name == group_name ]
    if len(matching) < 1:
        raise ValueError(f"Group name {group_name} doesn't match a known group!")
    if len(matching) > 1:
        # TODO #enhancement: either disallow duplicate group names earlier, or add an
        # extra interactive step to select a group based on a preview of its contents.
        raise ValueError(f"Group name {group_name} matches multiple groups!")
    matching = matching[0]

    print(matching)
    # TODO #finish
    raise NotImplementedError(f"pause({group_name})")


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

    args: argparse.Namespace = parser.parse_args()

    if args.command is None:
        # if we weren't given a command, then `args` won't have properties for the
        # common arguments to the next parsing step will fail.
        print("Please provide a command, or -h/--help to print help.",
              file=sys.stderr)
        return

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
        case 'list':
            blocked_filter: bool | None = None
            if args.blocked:
                blocked_filter = True
            if args.unblocked:
                blocked_filter = False

            ls(blocked_filter, bf_path, should_colour)


if __name__ == '__main__':
    try:
        main()
        sys.stdout.flush()
    except BrokenPipeError:
        # python flushes standard streams on exit; redirect remaining output to
        # /dev/null to avoid another BrokenPipeError at shutdown.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())