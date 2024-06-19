#!/bin/bash

# TODO #cleanup


# install required python deps
command -v python3 > /dev/null || sudo apt install python3
command -v pip3 > /dev/null || sudo apt install python3-pip

if ! sudo -H pip3 show inotify_simple > /dev/null 2>&1; then
    sudo -H pip3 install inotify_simple --break-system-packages
fi

required_python_minor=10
python_minor="$(/usr/bin/env python3 -c 'import sys; print(sys.version_info.minor)')"
if [ "$python_minor" -lt "$required_python_minor" ]; then
    >&2 echo your python version is too old!
    >&2 echo need at least version 3."$required_python_minor", but got 3."$python_minor"
    exit 1
fi

# install and enable the systemd service (for run-on-startup)
sudo cp i-am-making-a-bad-decision.service /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable i-am-making-a-bad-decision.service &&
sudo systemctl start i-am-making-a-bad-decision.service