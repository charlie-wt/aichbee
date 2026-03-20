* [~] cli
    * [x] listing block groups.
    * [x] showing which groups are currently active.
    * [~] refactor handling `sudo`.
        * [x] probably always default to looking in the right file location for
              the blockfile.
        * [ ] only require `sudo` for those operations that need it (basically
              just `pause`?)
    * [ ] new syntax to allow specifying that a group can be unblocked for
          a certain period—eg. "i can only access these sites for 1hr per
          {day,week,month...}".
        * [ ] also allow setting an unlimited duration, for if people just want
              a bit of extra friction.
        * should reactivate everything on quit?
        * [ ] also allow, when unblocking, to specify how long to unblock for.
            * eg. `$ aichbee pause "daily" --for 1hr`