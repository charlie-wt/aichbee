import base64
from dataclasses import dataclass, field
from datetime import datetime as dt, timedelta
from enum import Enum, auto
import logging
import os
from pathlib import Path
import pickle

from blocktime import Time, TimeRange, within_constraints
import util


class DurationPeriod(Enum):
    ''' The period over which a duration-based constraint can apply before resetting.
    '''

    DAY   = auto()
    WEEK  = auto()
    MONTH = auto()

    def from_str (string: str) -> 'DurationPeriod':
        ''' Parse ``string`` into a ``DurationPeriod`` (based on it being the prefix of
        a period), or raise a ``ValueError`` if it can't be done.
        '''
        return util.get_unique_enum_prefix_match(
            string, DurationPeriod, value_name="duration period")

    def ready_to_reset (self, prev_reset: dt, now: dt) -> bool:
        ''' If the current time is ``now``, and this ``DurationPeriod`` last reset at
        time ``prev_reset``, is it ready to reset again?

        :param prev_reset: When did we last reset, to compare to 'now'?
        :param now: Date-time to treat as 'now'.
        :returns: Whether this ``DurationPeriod`` should 'reset'/roll over.
        '''

        def with_timedelta (*args, **kwargs) -> bool:
            return now - prev_reset > timedelta(*args, **kwargs)

        match self:
            case DurationPeriod.DAY:
                return with_timedelta(days=1)
            case DurationPeriod.WEEK:
                return with_timedelta(weeks=1)
            case DurationPeriod.MONTH:
                return now.year > prev_reset.year or now.month > prev_reset.month

        raise NotImplementedError(f"Need to implement ready_to_reset for {self}.")


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
    is_paused: bool = False
    prev_duration_reset: dt | None = None
    duration_remaining: timedelta | None = None
    # TODO #verify: to actually make things robust to crashes, does this need to be part
    # of some separate 'transient state', not this 'durable state' that gets saved to a
    # file?
    prev_duration_remaining_update: dt | None = None

    def reset_duration(self, now: dt, duration: Duration) -> None:
        self.prev_duration_reset = now
        self.duration_remaining = timedelta(hours=duration.length_hours)
        self.prev_duration_remaining_update = now


@dataclass
class BlockGroup:
    ''' A group of sites to block, with the constraints with which to block them. '''

    # config
    name: str | None
    sites: list[str] = field(default_factory=list)
    schedule_ranges: list[TimeRange] = field(default_factory=list)
    duration: Duration | None = None
    config_filename: str = ""

    # state
    state: State = field(default_factory=State)


    def display_name (self) -> str:
        return self.name or '(unnamed group)'

    def state_path (self) -> Path:
        if self.name is None:
            raise ValueError("Tried to get the state path of an unnamed block group. "
                             "Any block group with a duration-based constraint (and "
                             "thus needing to save state) must have a unique name.")

        canonical_name: str = self.config_filename + self.name
        filename: str = base64.b64encode(bytes(canonical_name, 'utf-8')).decode('utf-8')

        # TODO #correctness: should this be `state_dir`; it's likely gonna be made by (&
        # thus owned by) root; feels like it should then be put somewhere more root-y?
        return util.state_dir() / filename

    def is_blocking (self, now: dt | None = None) -> bool:
        ''' If the current time is `now`, should this group's blocks be applied? '''
        return self.within_all_constraints(now) and not self.state.is_paused

    def within_all_constraints (self, now: dt | None = None) -> bool:
        ''' If the current time is `now`, do all of our constraints say our blocks
        should be applied? '''
        if now is None:
            now = dt.now()
        return (self.within_duration_constraints(now) or
                self.within_schedule_constraints(now))

    def within_duration_constraints (self, now: dt) -> bool:
        ''' If the current time is `now`, does the group's duration constraint say the
        blocks should be applied (if it exists)?
        '''
        if self.duration is None:
            return False

        if (self.state.prev_duration_reset is None or
            self.state.duration_remaining is None or
            self.duration.period.ready_to_reset(now, self.state.prev_duration_reset)
           ):
            return False

        return self.state.duration_remaining.total_seconds() <= 0

    def update_state (self, now: dt | None = None) -> None:
        if self.duration is None:
            return

        if now is None:
            now = dt.now()

        if self.state.is_paused or self.within_schedule_constraints(now):
            return

        if (
            self.state.prev_duration_reset is None or
            self.state.duration_remaining is None or
            self.state.prev_duration_remaining_update is None or
            self.duration.period.ready_to_reset(self.state.prev_duration_reset, now)
        ):
            self.state.reset_duration(now, self.duration)

        to_deduct: timedelta = now - self.state.prev_duration_remaining_update
        self.state.duration_remaining -= to_deduct
        self.state.prev_duration_remaining_update = now

        self.save_state()

    def save_state (self) -> None:
        ''' Save duration-constraint state to this group's standardised file.

        Note: will raise a ``ValueError`` if this group has no name: any block group
        that needs to save state must have a unique name.
        '''
        self.state_path().parent.mkdir(mode=0o775, parents=True, exist_ok=True)
        with open(self.state_path(), 'wb') as f:
            pickle.dump(self.state, f)

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
        self.update_state()
        self.state.is_paused = True
        self.save_state()

    def unpause (self) -> None:
        self.state.is_paused = False
        self.save_state()
        self.update_state()

    def within_schedule_constraints (self, now: dt) -> bool:
        ''' If the current time is `now`, do the group's schedule constraints say the
        blocks should be applied?
        '''

        return within_constraints(Time.from_dt(now), self.schedule_ranges)

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

        res += '\tSites to block:\n'
        for s in self.sites:
            res += f'\t\t{s}\n'

        return res
