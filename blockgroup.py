import base64
from dataclasses import dataclass, field
from datetime import datetime as dt, timedelta, date
from enum import Enum, auto
import logging
import os
from pathlib import Path
import pickle

from schedule import next_change_time, Time, TimeRange, within_constraints
import util


class DurationPeriod(Enum):
    ''' The period over which a duration-based constraint can apply before resetting.
    '''

    PER_DAY   = auto()
    PER_WEEK  = auto()
    PER_MONTH = auto()
    EACH_DAY   = auto()
    EACH_WEEK  = auto()
    EACH_MONTH = auto()

    def from_str (string: str) -> 'DurationPeriod':
        ''' Parse ``string`` into a ``DurationPeriod`` (based on it being the prefix of
        a period), or raise a ``ValueError`` if it can't be done.
        '''
        return util.get_unique_enum_prefix_match(
            string, DurationPeriod, value_name="duration period")

    def next_reset_at (self, prev_reset: dt) -> dt:
        ''' If this ``DurationPeriod`` last reset at time ``prev_reset``, at what point
        will it next be ready to reset again?

        :param prev_reset: When did we last reset, to compare to 'now'?
        :returns: When this ``DurationPeriod`` should next 'reset'/roll over.
        '''

        def after_timedelta (*args, **kwargs) -> dt:
            return prev_reset + timedelta(*args, **kwargs)

        def midnight (d: date) -> dt:
            return dt.combine(d, dt.min.time())

        match self:
            # `PER_x`: get 1 `x` after the previous reset
            case DurationPeriod.PER_DAY:
                return after_timedelta(days=1)
            case DurationPeriod.PER_WEEK:
                return after_timedelta(weeks=1)
            case DurationPeriod.PER_MONTH:
                return after_timedelta(months=1)
            # `EACH_x`: get the start of the next `x` after previous reset, at midnight
            case DurationPeriod.EACH_DAY:
                return midnight(prev_reset.date() + timedelta(days=1))
            case DurationPeriod.EACH_WEEK:
                return midnight(
                    prev_reset.date() + timedelta(days=(7 - prev_reset.weekday()))
                )
            case DurationPeriod.EACH_MONTH:
                return midnight(
                    (prev_reset.replace(day=1) + timedelta(days=32)).replace(day=1).date()
                )

        raise NotImplementedError(f"Need to implement next_reset_at for {self}.")

    def ready_to_reset (self, prev_reset: dt, now: dt) -> bool:
        ''' If the current time is ``now``, and this ``DurationPeriod`` last reset at
        time ``prev_reset``, is it ready to reset again?

        :param prev_reset: When did we last reset, to compare to 'now'?
        :param now: Date-time to treat as 'now'.
        :returns: Whether this ``DurationPeriod`` should 'reset'/roll over.
        '''

        return now > self.next_reset_at(prev_reset)


@dataclass
class Duration:
    ''' A duration-based constraint. '''

    period: DurationPeriod
    length_hours: float

    def __str__ (self) -> str:
        maybe_plural = "s" if self.length_hours != 1 else ""
        return f"{self.length_hours} hour{maybe_plural} per {self.period.name.lower()}"


@dataclass
class State:
    prev_duration_reset: dt | None = None
    time_spent_paused: timedelta | None = None

    def reset_duration(self, now: dt, duration: Duration) -> None:
        self.prev_duration_reset = now
        self.time_spent_paused = timedelta()


@dataclass
class BlockGroup:
    ''' A group of sites to block, with the constraints with which to block them. '''

    # config
    name: str | None
    sites: list[str] = field(default_factory=list)
    schedule_ranges: list[TimeRange] = field(default_factory=list)
    duration: Duration | None = None
    config_path: Path = field(default_factory=Path)

    # persistent state
    state: State = field(default_factory=State)

    # transient state
    is_paused: bool = False
    prev_time_spent_paused_update: dt | None = None

    def display_name (self) -> str:
        ''' Get a string (either group name or a placeholder) suitable for printing. '''
        return self.name or '(unnamed group)'

    def canonical_name (self) -> str:
        ''' Get a name that should (hopefully) be unique even if we've run aichbee with
        different configurations. '''
        return str(self.config_path.resolve()) + "::" + self.name

    def state_filename (self) -> str:
        ''' Get the filename (not including directories) of this group's state file. '''
        return base64.b64encode(bytes(self.canonical_name(), 'utf-8')).decode('utf-8')

    def state_path (self) -> Path:
        ''' Get the full path to this group's state file.

        Note: will raise a ``ValueError`` if this group has no name: any block group
        that needs to save state must have a unique name.
        '''
        if self.name is None:
            raise ValueError("Tried to get the state path of an unnamed block group. "
                             "Any block group with a duration-based constraint (and "
                             "thus needing to save state) must have a unique name.")

        return util.state_dir() / self.state_filename()

    def duration_remaining (self) -> timedelta | None:
        ''' Get the amount of time remaining on our duration-based constraint, if we
        have one.

        Note that if we've exceeded our allowed duration, this result will be negative.
        '''
        if self.duration is None:
            return None

        spent_paused = self.state.time_spent_paused
        if spent_paused is None:
            spent_paused = timedelta()

        return timedelta(hours=self.duration.length_hours) - spent_paused

    def duration_summary (self) -> str | None:
        ''' Get a human-readable summary of the state of our duration constraint, if we
        have one.
        '''
        remaining: timedelta | None = self.duration_remaining()

        if remaining is None:
            return None

        remaining = max(timedelta(), remaining)  # don't go under 00:00:00

        res: str = f"{remaining} remaining"

        if self.state.prev_duration_reset is not None:
            # we can't say when the next reset will be if we've not reset before
            until = self.duration.period.next_reset_at(self.state.prev_duration_reset)
            res = f"{res} until {until.replace(microsecond=0)}"

        return res

    def is_blocking (self, now: dt | None = None) -> bool:
        ''' If the current time is ``now`` (defaulting to the current time), should this
        group's blocks be applied?
        '''
        if now is None:
            now = dt.now()

        if self.within_schedule_constraints(now):
            return True

        if self.duration is not None:
            return self.within_duration_constraints(now) or not self.is_paused

        return False

    def within_duration_constraints (self, now: dt) -> bool:
        ''' If the current time is ``now``, does the group's duration constraint say the
        blocks should be applied (if it exists)?
        '''
        if self.duration is None:
            return False

        if (self.state.prev_duration_reset is None or
            self.state.time_spent_paused is None or
            self.duration.period.ready_to_reset(now, self.state.prev_duration_reset)
           ):
            return False

        return self.duration_remaining().total_seconds() <= 0

    def within_schedule_constraints (self, now: dt) -> bool:
        ''' If the current time is ``now``, do the group's schedule constraints say the
        blocks should be applied?
        '''

        # If we have *just* a duration constraint, then we should never constrain based
        # on schedule.
        if self.duration is not None and len(self.schedule_ranges) == 0:
            return False

        return within_constraints(Time.from_dt(now), self.schedule_ranges)

    def next_schedule_change (self, now: dt) -> dt | None:
        ''' If the current date & time is ``now``, get the next time when one of our
        schedule constraints will change from blocked to unblocked, or vice versa.

        If this block group has no schedule constraints, will return ``None``.
        '''
        if len(self.schedule_ranges) == 0:
            return None
        return min(next_change_time(now, r) for r in self.schedule_ranges)

    def update_state (self, now: dt | None = None) -> None:
        ''' Update this group's ``state`` assuming the current time is now ``now``, and
        (if needed) save it to its file.
        '''
        if self.duration is None:
            return

        if now is None:
            now = dt.now()

        if self.is_paused:
            # Update paused duration, only if we're also outside schedule constraints.
            if not self.within_schedule_constraints(now):
                if (
                    self.state.prev_duration_reset is None or
                    self.state.time_spent_paused is None or
                    self.duration.period.ready_to_reset(self.state.prev_duration_reset,
                                                        now)
                ):
                    self.state.reset_duration(now, self.duration)

                if self.prev_time_spent_paused_update is not None:
                    to_add: timedelta = now - self.prev_time_spent_paused_update
                    self.state.time_spent_paused += to_add

            # If we run out of time while paused, then automatically unpause.
            if self.within_duration_constraints(now):
                self.is_paused = False

        # Finish
        self.prev_time_spent_paused_update = now
        self.save_state()

    def save_state (self) -> None:
        ''' Save duration-constraint state to this group's standardised file.

        Note: will raise a ``ValueError`` if this group has no name: any block group
        that needs to save state must have a unique name.
        '''
        with open(self.state_path(), 'wb') as f:
            pickle.dump(self.state, f)
        os.chmod(self.state_path(), 0o775)

    def load_state (self) -> None:
        ''' Load duration-constraint state from this group's standardised file.

        Note: will raise a ``ValueError`` if this group has no name: any block group
        that needs to save state must have a unique name.
        '''
        if not self.state_path().exists():
            return
        with open(self.state_path(), 'rb') as f:
            self.state = pickle.load(f)

    def pause (self) -> None:
        ''' Pause this group's blocking. '''
        self.is_paused = True
        self.update_state()

    def unpause (self) -> None:
        ''' Unpause this group's blocking. '''
        self.is_paused = False
        self.update_state()

    def schedule_constraints_consistent (self) -> bool:
        '''
        Are this group's (schedule-based) constraints consistent with each other?

        Currently, returns ``False`` if any of the time-only constraints (eg. "@ 01:00 -
        02:00") *or* any of the day-based constraints (eg. "@ mon 03:00 - fri 04:00")
        overlap at all in time (they're checked independently).
        '''

        def ranges_consistent (ranges: list[TimeRange]) -> bool:
            ''' Is the given set of ranges consistent with itself? '''

            for i in range(len(ranges)):
                for j in range(len(ranges)):
                    if i == j:
                        continue

                    bad_start = within_constraints(ranges[i].start, ranges[j])
                    bad_end = within_constraints(ranges[i].end, ranges[j])

                    if bad_start or bad_end:
                        logging.debug(f'constraints for group {self.display_name()}: ',
                                      f'{ranges[i]} vs. {ranges[j]}: ',
                                      f'bad start: {bad_start}, bad end: {bad_end}')
                        return False
            return True

        # check time-based, and day-based ranges against each other separately
        time_only_ranges = []
        day_based_ranges = []
        for r in self.schedule_ranges:
            if r.time_only():
                time_only_ranges.append(r)
            else:
                day_based_ranges.append(r)

        return (ranges_consistent(time_only_ranges) and
                ranges_consistent(day_based_ranges))

    def __str__ (self) -> str:
        res = f'Group "{self.display_name()}":\n'

        res += '\tSchedule constraints:\n'
        for r in self.schedule_ranges:
            res += f'\t\t{r}\n'

        res += '\tDuration constraint:\n'
        if self.duration is None:
            res += "\t\t(none)\n"
        else:
            res += f'\t\t{self.duration}\n'

        # Ellipsise the list of sites if it's too long (unless we're printing verbosely)
        max_sites_to_list: int = 10
        sites_to_list: list[str] = self.sites
        if (
            len(sites_to_list) > max_sites_to_list and
            logging.root.level >= logging.DEBUG
        ):
            sites_to_list = self.sites[:max_sites_to_list // 2]
            sites_to_list.append(f"... {len(self.sites) - max_sites_to_list} more sites ...")
            sites_to_list.extend(self.sites[-(max_sites_to_list // 2 + 1):-1])

        res += '\tSites to block:\n'
        for s in sites_to_list:
            res += f'\t\t{s}\n'

        return res
