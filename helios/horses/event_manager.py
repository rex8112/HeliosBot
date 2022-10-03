from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import discord
from dateutil.relativedelta import *

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

    @staticmethod
    def get_start_of_week() -> datetime:
        monday = datetime.now().astimezone()
        monday = monday + relativedelta(weekday=MO(-1))
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        return monday

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
        if len(self.get_weekly_events()) > 0:
            grade3 = 1
        else:
            grade3 = 0
        stakes = races_to_run - grade3 - listed - maidens

        races = RaceTypeCount(maidens=maidens, stakes=stakes, listed=listed,
                              grade3=grade3)
        new_event = Event(self, self.stadium.daily_channel,
                          event_type='daily',
                          start_time=start_time,
                          races=races)
        new_event.name = f'{start_time.strftime("%A")} Daily Event'
        return new_event

    def create_weekly_event(self, horses: dict[int, 'Horse']):
        now = datetime.now().astimezone()
        sunday = now + relativedelta(days=+1, weekday=SU)
        start_time = sunday.replace(hour=20, minute=0, second=0, microsecond=0)

        maiden_horses = []
        graded_horses = []
        registered_horses = []
        for horse in horses.values():
            if horse.get_flag('MAIDEN'):
                maiden_horses.append(horse)
            else:
                graded_horses.append(horse)
                if horse.owner is None or horse.get_flag('REGISTERED'):
                    registered_horses.append(horse)
        possible_maidens = len(maiden_horses) // 12
        possible_graded = len(graded_horses) // 12
        possible_registered = len(registered_horses) // 12
        max_races = 24

        maiden_races = min(6, possible_maidens)
        listed_races = min(2, possible_graded)
        if possible_graded > 2:
            grade3_races = min(2, possible_graded)
        else:
            grade3_races = 0
        grade2_races = min(1, possible_registered)
        stakes_races = (max_races
                        - grade2_races
                        - grade3_races
                        - listed_races
                        - maiden_races)

        races = RaceTypeCount(maidens=maiden_races, stakes=stakes_races,
                              listed=listed_races, grade3=grade3_races,
                              grade2=grade2_races)
        event = Event(self, self.stadium.event_channel,
                      event_type='weekly',
                      start_time=start_time,
                      races=races)
        event.settings['announcement_time'] = 60 * 60 * 36
        event.settings['registration_time'] = 60 * 60 * 24
        event.settings['betting_time'] = 60 * 60 * 2
        event.name = f'{start_time.strftime("%b %d")} Weekly Event'
        return event

    async def new_day(self):
        now = datetime.now().astimezone()
        sunday = now + relativedelta(weekday=SU)
        delta = sunday - now
        if sunday > now and delta.days > 4:
            weekly = self.get_weekly_events()
            if len(weekly) < 1:
                self.stadium.new_season()
                event = self.create_weekly_event(
                    self.stadium.unowned_qualified_horses()
                )
                self.add_event(event)

        event_today = False
        for event in self.events:
            if event.start_time.date() == now.date():
                event_today = True
                return

        daily = self.create_daily_event(
            self.stadium.unowned_qualified_horses()
        )
        self.add_event(daily)

    async def manage(self) -> bool:
        result = False
        for event in self.events:
            if await event.manage_event():
                result = True
        return result

    async def close_event(self, event: Event):
        embed = discord.Embed(
            colour=discord.Colour.red(),
            title=f'{event.name} has Ended!',
            description=('Congratulate our winners!\n\n'
                         f'{event.settings["winner_string"]}')
        )
        try:
            await event.channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            ...

        if event.type == 'weekly':
            self.stadium.close_season()
            for horse in self.stadium.registered_horses().values():
                horse.set_flag('REGISTERED', False)
                await horse.save()

        for race in event.races:
            try:
                event.stadium.races.remove(race)
            except ValueError:
                ...
        self.remove_event(event)

    async def save(self):
        await self.stadium.save()

    def to_json(self):
        return [x.to_json() for x in self.events]

    def fill_events_from_json(self, data: list):
        self.events.extend([Event.from_json(self, x) for x in data])

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

    def get_weekly_events(self):
        weekly_events = []
        for event in self.events:
            if event.type == 'weekly':
                weekly_events.append(event)
        return weekly_events

    def add_event(self, event: Event):
        if event not in self.events:
            self.events.append(event)

    def remove_event(self, event: Event):
        """Remove event from manager, silently ignores value errors"""
        try:
            self.events.remove(event)
        except ValueError:
            ...
