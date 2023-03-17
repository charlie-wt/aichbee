#!/usr/bin/env python3

import argparse
from functools import lru_cache

import blockfile
from blockgroup import BlockGroup


@lru_cache()
def groups() -> list[BlockGroup]:
    # TODO #correctness: allow customising filename, as with the service.
    return blockfile.read(blockfile.get_filename())


def pause(group_name: str) -> None:
    matching = [ g for g in groups() if g.name == group_name ]
    if len(matching) < 1:
        raise ValueError(f"Group name {group_name} doesn't match a known group!")
    if len(matching) > 1:
        raise ValueError(f"Group name {group_name} matches multiple groups!")
    matching = matching[0]

    print(matching)
    # TODO #finish
    raise NotImplementedError(f"pause({group_name})")


def main ():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_pause = subparsers.add_parser(
        "pause",
        help="Pause the given block group, if allowed.")
    parser_pause.add_argument(
        "pause block group",
        help="Name of the block group to pause.")

    args = parser.parse_args()

    pbg = getattr(args, 'pause block group', None)
    if pbg is not None:
        pause(pbg)


if __name__ == '__main__':
    main()