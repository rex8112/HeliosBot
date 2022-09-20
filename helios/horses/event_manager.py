from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .event import Event, RaceTypeCount

if TYPE_CHECKING:
    from .horse import Horse
    from ..stadium import Stadium


class EventManager:
    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self.events: list[Event] = []

    @property
    def server(self):
        return self.stadium.server

    @property
    def bot(self):
        return self.server.bot

    def create_daily_event(self, horses: dict[int, 'Horse']):
        now = datetime.now().astimezone()
        start_time = now.replace(hour=21, minute=0, second=0,
                                 microsecond=0)
        if now + timedelta(hours=1) >= start_time:
            start_time += timedelta(days=1)

        eligible_horses = horses
        maiden_horses = []
        listed_horses = []
        for horse in eligible_horses.values():
            if horse.get_flag('MAIDEN'):
                maiden_horses.append(horse)
            else:
                listed_horses.append(horse)
        possible_races = len(eligible_horses) // 12
        possible_maidens = len(maiden_horses) // 12
        possible_listed = len(listed_horses) // 12
        max_races = 12
        races_to_run = min(max_races, possible_races)

        maidens = min(3, possible_maidens)
        listed = min(1, possible_listed)
        stakes = races_to_run - listed - maidens

        races = RaceTypeCount(maidens=maidens, stakes=stakes, listed=listed)
        new_event = Event(self, self.stadium.daily_channel,
                          event_type='daily',
                          start_time=start_time,
                          races=races)
        new_event.name = f'{start_time.strftime("%A")} Daily Event'
        return new_event

    async def new_day(self):
        ...

    async def manage(self) -> bool:
        result = False
        for event in self.events:
            if await event.manage_event():
                result = True
        return result

    async def save(self):
        await self.stadium.save()

    def to_json(self):
        return [x.to_json() for x in self.events]

    def fill_events_from_json(self, data: list):
        self.events.extend([Event.from_json(self.stadium, x) for x in data])

    @classmethod
    def from_json(cls, stadium: 'Stadium', data: list):
        em = cls(stadium)
        em.fill_events_from_json(data)
        return em

    def get_daily_events(self):
        daily_events = []
        for event in self.events:
            if event.type == 'daily':
                daily_events.append(event)
        return daily_events

    def add_event(self, event: Event):
        if event not in self.events:
            self.events.append(event)

    def remove_event(self, event: Event):
        """Remove event from manager, silently ignores value errors"""
        try:
            self.events.remove(event)
        except ValueError:
            ...
