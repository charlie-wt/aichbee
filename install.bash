#!/usr/bin/env bash


# utils
yesno () {
    local qn="$1"
    local default="$2"

    # set our default based on input
    local opts="[y/n]"
    if [ "$default" = y ]; then
        local opts="[Y/n]"
    elif [ "$default" = n ]; then
        local opts="[y/N]"
    fi

    while true; do
        # read input
        read -p "$qn $opts " -n 1 -s -r input < /dev/tty
        echo ${input}

        # if nothing entered and have a default, return it
        if [[ -z "$input" && ! -z "$default" ]]; then
            [ "$default" = "y" ] && return 0 || return 1
        fi

        # else if something entered, return if valid
        if [[ "$input" =~ ^[yYnN]$ ]]; then
            input=${input:-${default}}
            [[ "$input" =~ ^[yY]$ ]] && return 0 || return 1
        fi
    done
}

warn () { echo -e "\e[33m""$@""\e[0m"; }
info () { echo -e "\e[36m""$@""\e[0m"; }

# install python if needed & desired
if ! command -v python3 > /dev/null &&
   yesno "install python (via $(warn apt))?" ; then
    sudo apt install python3 -y
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

src_location=$(dirname "$(readlink -e "$0")")
esc_src_location=${src_location//\//\\/}  # escape slashes to not upset `sed`
cp "$src_location/$template_filename" "$src_location/$service_filename"
sed -i "s/$src_location_template_var/$esc_src_location/g" "$src_location/$service_filename"
sed -i "1s/^/$generated_file_message\n\n/" "$src_location/$service_filename"

# install and enable the systemd service (for run-on-startup)
sudo cp "$src_location/$service_filename" /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable "$service_filename" &&
sudo systemctl start "$service_filename"

# install the cli
desired_link="$HOME/.local/bin/aichbee"
link_target="$src_location/cli.py"
if ! [[ -L "$desired_link" && "$(readlink -f "$desired_link")" == "$link_target" ]]; then
    destination_exists_text=""
    [ -e "$desired_link" ] && destination_exists_text=" ($(warn WARNING): a file already exists at the destination!)"
    if yesno "Make a symlink from $(info "$desired_link") to the CLI script at $(info "$link_target")?$destination_exists_text" y ; then
        [ -e "$desired_link" ] && rm "$desired_link"
        ln -s "$link_target" "$desired_link"
    fi
fi


echo "$(info INSTALLED)"
echo " * $(warn NOTE): if you move this folder, you'll have to run the script again."
