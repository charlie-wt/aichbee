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

# create service file from template, based on wherever this script's located
template_filename="aichbee.service.template"
service_filename="${template_filename%.template}"
src_location_template_var="<<SRC_LOC>>"
generated_file_message="# THIS FILE IS GENERATED: PLEASE MODIFY "$template_filename" INSTEAD"

cp "$template_filename" "$service_filename"
src_location=$(dirname "$(readlink -e "$0")")
src_location=${src_location//\//\\/}  # escape slashes to not upset `sed`
sed -i "s/$src_location_template_var/$src_location/g" "$service_filename"
sed -i "1s/^/$generated_file_message\n\n/" "$service_filename"

# install and enable the systemd service (for run-on-startup)
sudo cp "$service_filename" /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable "$service_filename" &&
sudo systemctl start "$service_filename"

echo -e "\e[36mINSTALLED\e[0m"
echo -e " * \e[33mNOTE\e[0m: if you move this folder, you'll have to run the script again."
