#!/usr/bin/env bash

scr="/home/charlie/Programming/python/hb"
dir=${1:-"/etc"}
fname=${2:-"hosts"}
blocklist=${3:-"blocklist.txt"}

# TODO - port to shell script, not external python program
python3 $scr/refresh.py "$dir/$fname" "$scr/$blocklist"

# got this from https://superuser.com/a/181543 lol
inotifywait -e close_write -m $dir |
while read -r directory events filename; do
  if [ "$filename" = "$fname" ]; then
    python3 $scr/refresh.py "$dir/$fname" "$scr/$blocklist"
  fi
done