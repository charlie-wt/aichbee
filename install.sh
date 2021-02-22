#!/bin/bash

# install required python modules
if command -v pip3 > /dev/null; then
  if ! sudo -H pip3 show inotify_simple > /dev/null; then
    sudo -H pip3 install inotify_simple
  fi
else
  sudo apt install python3-pip &&
  sudo -H pip3 install inotify_simple
fi

# install and enable the systemd service (for run-on-startup)
sudo cp i-am-making-a-bad-decision.service /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable i-am-making-a-bad-decision.service &&
sudo systemctl start i-am-making-a-bad-decision.service