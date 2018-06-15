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
* slightly more unify technologies used.
	* just python: could possibly use `python3-pyinotify` package to do what the bash currently does.
	* just bash: could get messy trying to do all the blocklist parsing/applying schedules, bash not really made for that sort of thing. limits platform-agnosticism.
	* just C: would be sort of nice as an exercise, and is always better for the user if it takes fewer resources (provided no memory issues etc.), but this sort of program really feels more suited to a scripting language.
	* one benefit of this: gives a way of limiting the ability to edit the blocklist, for free.
		* currently, the continuous part of the program (watching the hosts file) is separate from the 'read in the blocklist and use it to edit the hosts file' part, which is invoked. unifying the parts makes it easy to keep the blocklist in memory after a single read at the start.
* allow blocking of launching programs as well as websites.
* graphical front-end.
* support for different systems (non-systemd, macOS, windows)
