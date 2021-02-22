from dataclasses import dataclass, field

from blocktime import Time, within_time


@dataclass
class BlockGroup:
    ''' a group of sites to block, with the time constraints with which to block them.

    '''

    name: str
    sites: [str] = field(default_factory=list)
    starts: [Time] = field(default_factory=list)
    ends: [Time] = field(default_factory=list)

    def within_time (self, now: Time = None) -> bool:
        ''' if the current time is `now`, should this group's blocks be applied? '''
        return within_time(now, self.starts, self.ends)
