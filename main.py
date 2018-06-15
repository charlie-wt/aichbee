#!/usr/bin/env python3

import sys
from inotify_simple import INotify, flags
import refresh

def main ():
    num_args = len(sys.argv)

    # file to watch (default /etc/hosts)
    to_refresh = '/etc/hosts'
    if num_args >= 2: to_refresh = sys.argv[1]
    ref_dir  = to_refresh[:to_refresh.rfind('/')+1]
    ref_file = to_refresh[to_refresh.rfind('/')+1:]

    # location of blocklist file (default ./blocklist.txt)
    blocks = None
    if num_args >= 3:
        blocks = refresh.read_block_file(sys.argv[2])
    else:
        blocks = refresh.read_block_file('./blocklist.txt')

    # configure inotify
    inotify = INotify()
    watch_flags = flags.MODIFY
    wd = inotify.add_watch(ref_dir, watch_flags)

    # read events, maybe respond
    while True:
        for event in inotify.read():
            if event[3] == ref_file:
                refresh.refresh(to_refresh, blocks)

if __name__ == '__main__':
    main()
