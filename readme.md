# aichbee

a website blocker.

## dependencies

* python 3
* inotify-tools
* systemd

## todo

### definitely
* automatically unblock in off-time, instead of just allowing one to unblock.
* implement multiple time constraints on a group (so long as they don't clash).
* limit the ability to edit the blocklist and have the changes be recognised by the program.
	* maybe just make it take a day/reboot/something for changes to the blockfile to be recognised?
	* could only allow at times when blocks are off
		* this wouldn't work for blocklists that are always-on, and could be confusing as blocklist schedules get more complex.

### maybe
* allow blocking of launching programs as well as websites.
* graphical front-end.
* support for different systems (non-systemd, macOS, windows)
