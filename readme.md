# aichbee

a website blocker.

for an example of the config file syntax, see [example-blockfile](example-blockfile).

## dependencies

* python 3
	* [inotify_simple](https://pypi.org/project/inotify_simple/)
* systemd

## todo

### definitely

* on [durational](https://github.com/charlie-wt/aichbee/tree/durational) branch:
    * cli (inspecting, pausing groups)
    * duration-based constraints

### maybe

* allow blocking of launching programs as well as websites.
* graphical front-end.
* support for different systems (non-systemd, macOS, windows)
