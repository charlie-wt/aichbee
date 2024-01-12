from dataclasses import dataclass, field

from blocktime import Time, TimeRange, within_constraints


@dataclass
class BlockGroup:
    ''' a group of sites to block, with the time constraints with which to block them.

    '''

    name: str | None
    sites: list[str] = field(default_factory=list)
    ranges: list[TimeRange] = field(default_factory=list)


    def display_name (self) -> str:
        return self.name or '(unnamed group)'


    def within_constraints (self, now: Time = None) -> bool:
        ''' if the current time is `now`, should this group's blocks be applied? '''
        return within_constraints(now, self.ranges)


    def constraints_consistent (self) -> bool:
        '''
        Are the constraints on the given block group consistent with each other?

        Currently, returns `False` if any of the time-only constraints (eg. "@ 01:00 -
        02:00") *or* any of the day-based constraints (eg. "@ mon 03:00 - fri 04:00")
        overlap at all in time (they're checked independently).

        '''

        def ranges_consistent (ranges: list[TimeRange]) -> bool:
            ''' is the given set of ranges consistent with itself? '''

            for i in range(len(ranges)):
                for j in range(len(ranges)):
                    if i == j:
                        continue

                    bad_start = within_constraints(ranges[i].start, ranges[j])
                    bad_end = within_constraints(ranges[i].end, ranges[j])

                    if bad_start or bad_end:
                        if verbose:
                            print(f'constraints for group {self.display_name()}: ',
                                  f'{ranges[i]} vs. {ranges[j]}: ',
                                  f'bad start: {bad_start}, bad end: {bad_end}')
                        return False
            return True

        # check time-based, and day-based ranges against each other separately
        time_only_ranges = []
        day_based_ranges = []
        for r in self.ranges:
            if r.time_only():
                time_only_ranges.append(r)
            else:
                day_based_ranges.append(r)

        return (ranges_consistent(time_only_ranges) and
                ranges_consistent(day_based_ranges))


    def __str__ (self) -> str:
        res = f'Group "{self.display_name()}":\n'

        res += '\tTime constraints:\n'
        for r in self.ranges:
            res += f'\t\t{r}\n'

        res += '\tSites to block:\n'
        for s in self.sites:
            res += f'\t\t{s}\n'

        return res
