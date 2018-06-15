#!/bin/bash

# install required python modules
if command -v pip3 > /dev/null; then
  if ! sudo -H pip3 show inotify_simple > /dev/null; then
    sudo -H pip3 install inotify_simple
  fi
else
  sudo apt install pip3 &&
  sudo -H pip3 install inotify_simple
fi

# install and enable the systemd service (for run-on-startup)
sudo cp hb.service /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable hb.service &&
sudo systemctl start hb.service