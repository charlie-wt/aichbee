#!/bin/bash

sudo cp hb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hb.service