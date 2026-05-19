from enum import Enum, auto
import functools
import logging
import re

from blockgroup import BlockGroup


class BlockedState(Enum):
    """The state of a given blocked site in the watched file (ie. `hosts`)."""

    BLOCKED = auto()
    COMMENTED = auto()
    ABSENT = auto()


@functools.cache
def site_regex(site: str) -> re.Pattern:
    return re.compile(r"\s*(?P<comment_char>#\s*)?0.0.0.0\s+" + site)


def line_match(site: str, watchfile_line: str) -> BlockedState:
    if m := site_regex(site).match(watchfile_line):
        if m.group("comment_char") is None:
            return BlockedState.BLOCKED
        return BlockedState.COMMENTED
    return BlockedState.ABSENT


def blocked_state(site: str, watchfile_lines: list[str]) -> (BlockedState, list[int]):
    """
    Get the state of the given site, within the given 'watch file' lines (eg. those of
    ``hosts``).

    """

    blocked_lines = []
    commented_lines = []

    # Get the lines of `watchfile_lines` that contain (un)commented entries for `site`.
    for i, line in enumerate(watchfile_lines):
        state = line_match(site, line)

        if state == BlockedState.BLOCKED:
            blocked_lines.append(i)
            # Can't break, as the site may be in the file multiple times.
        elif state == BlockedState.COMMENTED:
            commented_lines.append(i)

    # Return list of line numbers based on blocked status of `site`.
    if blocked_lines:
        return (BlockedState.BLOCKED, blocked_lines)
    elif commented_lines:
        return (BlockedState.COMMENTED, commented_lines)
    return (BlockedState.ABSENT, [])


def block(filename: str, blocks: list[BlockGroup] | BlockGroup):
    """Main function to correct the hosts file."""
    if not isinstance(blocks, list):
        blocks = [blocks]

    # Get the data from the file.
    with open(filename, "r") as f:
        data = f.readlines()
    newdata = data[:]

    for group in blocks:
        logging.debug(f"group {group.display_name()}:")

        if not group.is_blocking():
            logging.debug("\tshouldn't be blocking right now")
            continue

        # This site should be blocked -- construct lines of new file.
        for site in group.sites:
            state, lines = blocked_state(site, data)

            # Site is already blocked.
            if state == BlockedState.BLOCKED:
                continue

            entry = f"0.0.0.0\t{site}\n"

            # Site is commented out -- uncomment.
            if state == BlockedState.COMMENTED:
                logging.debug(f"\t{entry[:-1]} is commented on lines {lines}")
                for l in lines:
                    newdata[l] = entry
                continue

            # Site is absent -- add.
            logging.debug(f"\t{entry[:-1]} is missing")
            newdata.append(entry)

    if data == newdata:
        # File has not changed - don't bother writing.
        logging.debug("-- nothing to update; don't write watched file")
    else:
        # Update the file.
        with open(filename, "w") as f:
            f.writelines(newdata)
        logging.debug("-- written updated watched file")


def unblock(filename: str, blocks: list[BlockGroup] | BlockGroup):
    """
    Unblock all websites in the blocks, applied one-by-one. To be used after a schedule
    finishes.

    """
    if not isinstance(blocks, list):
        blocks = [blocks]

    # Get the data from the file.
    with open(filename, "r") as f:
        data = f.readlines()
    newdata = data[:]

    for group in blocks:
        logging.debug(f"unblocking group {group.display_name()}:")

        # Construct lines of new file.
        blockentries = [f"#0.0.0.0\t{i}\n" for i in group.sites]
        for entry in blockentries:
            if entry not in data:
                if entry[1:] in data:
                    # Comment the line.
                    logging.debug(
                        f"\t{entry[1:-1]} is active at line {data.index(entry[1:])}"
                    )
                    newdata[data.index(entry[1:])] = entry

    if data == newdata:
        # File has not changed - don't bother writing.
        logging.debug("-- nothing's changed!")
    else:
        # Update the file.
        with open(filename, "w") as f:
            f.writelines(newdata)
        logging.debug("-- unblocked")
