import datetime
import math
from typing import TYPE_CHECKING

import discord
import numpy

from .race import Race
from ..tools.settings import Item

if TYPE_CHECKING:
    from ..stadium import Stadium
    from .horse import Horse
    from .event_manager import EventManager


class RaceTypeCount:
    def __init__(self, *,
                 maidens: int = 0,
                 stakes: int = 0,
                 listed: int = 0,
                 grade3: int = 0,
                 grade2: int = 0,
                 grade1: int = 0) -> None:
        """
        Represents the quantity of each type of race that the event should
        have.

        :param maidens: Amount of Maiden Races
        :param stakes: Amount of Stakes Races
        :param listed: Amount of Listed Grade Stakes Races
        :param grade3: Amount of Grade 3 Stakes Races
        :param grade2: Amount of Grade 2 Stakes Races
        :param grade1: Amount of Grade 1 Stakes Races
        """
        self.maidens: int = maidens
        self.stakes: int = stakes
        self.listed: int = listed
        self.grade3: int = grade3
        self.grade2: int = grade2
        self.grade1: int = grade1

    def get_total(self) -> int:
        return sum(self.to_json())

    def to_json(self) -> list[int]:
        return [
            self.maidens,
            self.stakes,
            self.listed,
            self.grade3,
            self.grade2,
            self.grade1
        ]

    @classmethod
    def from_json(cls, data: list[int]):
        c = cls(
            maidens=data[0],
            stakes=data[1],
            listed=data[2],
            grade3=data[3],
            grade2=data[4],
            grade1=data[5]
        )
        return c


class Event:
    def __init__(self,
                 event_manager: 'EventManager',
                 channel: discord.TextChannel,
                 *,
                 event_type: str = 'daily',
                 start_time: datetime.datetime,
                 betting_time: int = 60 * 60 * 1,
                 registration_time: int = 60 * 60 * 6,
                 announcement_time: int = 60 * 60 * 12,
                 races: RaceTypeCount):
        self.name = 'Unnamed Event'
        self.manager = event_manager
        self.channel = channel
        self.race_ids = []
        self.settings = {
            'type': event_type,
            'start_time': start_time.isoformat(),
            'betting_time': betting_time,
            'registration_time': registration_time,
            'announcement_time': announcement_time,
            'races': races.to_json(),
            'buffer': 5,
            'phase': 0,
            'winner_string': ''
        }

    def __key(self):
        return self.channel.id, self.settings['start_time'], self.race_ids

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Event):
            return self.__key() == other.__key()
        return NotImplemented

    @property
    def stadium(self):
        return self.manager.stadium

    @property
    def races(self):
        races = filter(lambda x: x.id in self.race_ids, self.stadium.races)
        races = list(sorted(races, key=lambda x: x.race_time))
        return races

    @property
    def type(self):
        return self.settings['type']

    @property
    def race_types(self) -> RaceTypeCount:
        return RaceTypeCount.from_json(self.settings['races'])

    @race_types.setter
    def race_types(self, value: RaceTypeCount):
        self.settings['races'] = value.to_json()

    @property
    def horses(self):
        races = self.races
        horses = []
        for r in races:
            horses.extend(r.horses)
        return horses

    @property
    def phase(self):
        return self.settings['phase']

    @phase.setter
    def phase(self, value: int):
        self.settings['phase'] = value

    @property
    def start_time(self) -> datetime.datetime:
        if isinstance(self.settings['start_time'], list):
            # noinspection PyTypeChecker
            return Item.deserialize(self.settings['start_time'],
                                    guild=self.stadium.guild,
                                    bot=self.stadium.server.bot)
        else:
            return datetime.datetime.fromisoformat(self.settings['start_time'])

    @start_time.setter
    def start_time(self, value: datetime.datetime):
        self.settings['start_time'] = value.isoformat()

    @property
    def betting_time(self) -> datetime.datetime:
        return (self.start_time
                - datetime.timedelta(seconds=self.settings['betting_time']))

    @property
    def registration_time(self) -> datetime.datetime:
        return (self.start_time
                - datetime.timedelta(
                    seconds=self.settings['registration_time']
                ))

    @property
    def announcement_time(self) -> datetime.datetime:
        return (self.start_time
                - datetime.timedelta(
                    seconds=self.settings['announcement_time']
                ))

    @property
    def races_finished(self):
        for race in self.races:
            if not race.finished:
                return False
        return True

    def create_maiden_race(self, race_time: datetime.datetime, index):
        race = Race.new(self.stadium, self.channel, 'maiden', race_time)
        race.can_run = False
        race.name = f'{self.name} Race {index}: Maiden Race'
        race.settings['purse'] = 1100
        race.settings['stake'] = int(1100 * 0.05)
        return race

    def create_stake_race(self, race_time: datetime.datetime, index):
        race = Race.new(self.stadium, self.channel, 'stake', race_time)
        race.can_run = False
        race.name = f'{self.name} Race {index}: Stakes Race'
        race.settings['purse'] = 1500
        race.settings['stake'] = int(1500 * 0.05)
        return race

    def create_listed_race(self, race_time: datetime.datetime, index):
        race = Race.new(self.stadium, self.channel, 'listed', race_time)
        race.can_run = False
        race.name = f'{self.name} Race {index}: Listed Race'
        race.settings['purse'] = 2000
        race.settings['stake'] = int(2000 * 0.05)
        return race

    def create_grade3_race(self, race_time: datetime.datetime, index):
        race = Race.new(self.stadium, self.channel, 'grade3', race_time)
        race.can_run = False
        race.name = f'{self.name} Race {index}: Grade 3 Race'
        race.settings['purse'] = 4000
        race.settings['stake'] = int(4000 * 0.05)
        return race

    def create_grade2_race(self, race_time: datetime.datetime, index):
        race = Race.new(self.stadium, self.channel, 'grade2', race_time)
        race.can_run = False
        race.name = f'{self.name} Race {index}: Grade 2 Race'
        race.settings['purse'] = 10000
        race.settings['stake'] = 0
        return race

    async def announce_event(self):
        schedule_string = ''
        for race in self.races:
            start_time = race.race_time
            schedule_string += (f'<t:{int(start_time.timestamp())}:t> - '
                                f'{race.max_horses} Horse {race.name}\n')
        embed = discord.Embed(
            colour=discord.Colour.green(),
            title=f'Announcing the {self.name}',
            description=(f'Registration opens for all races '
                         f'<t:{int(self.registration_time.timestamp())}:R>\n'
                         f'Betting opens for all races '
                         f'<t:{int(self.betting_time.timestamp())}:R>\n\n'
                         f'{schedule_string}')
        )
        await self.channel.send(embed=embed)
        self.phase += 1

    async def close_event(self):
        embed = discord.Embed(
            colour=discord.Colour.red(),
            title=f'{self.name} has Ended!',
            description=('Congratulate our winners!\n\n'
                         f'{self.settings["winner_string"]}')
        )
        await self.channel.send(embed=embed)
        for race in self.races:
            try:
                self.stadium.races.remove(race)
            except ValueError:
                ...
        self.manager.events.remove(self)

    async def maidens_available(self):
        maidens = 0
        for horse in self.stadium.horses.values():
            is_maiden = horse.is_maiden()
            if is_maiden:
                maidens += 1
        return maidens

    @staticmethod
    def prefill_races(races: list[Race],
                      horses: dict[int, 'Horse']) -> dict[int, 'Horse']:
        """
        Put random horses into the race that qualify
        :param races: A lit of races to be filled
        :param horses: A dict of horses to choose from
        :return: A copied dict with the used horses removed
        """
        horses = horses.copy()
        for race in races:
            qualified = list(filter(
                lambda x: race.is_qualified(x),
                horses.values()))
            if len(qualified) > 0:
                qualified_horses = list(
                    numpy.random.choice(qualified,
                                        min(race.max_horses, len(qualified)),
                                        replace=False))
            else:
                qualified_horses = []
            race.horses = qualified_horses
            for horse in qualified_horses:
                horses.pop(horse.id)
        return horses

    @staticmethod
    def prefill_races_weighted(races: list[Race],
                               horses: dict[int, 'Horse']
                               ) -> dict[int, 'Horse']:
        """
        Put random horses into the race that qualify, weighted by their quality
        :param races: A lit of races to be filled
        :param horses: A dict of horses to choose from
        :return: A copied dict with the used horses removed
        """
        horses = horses.copy()
        for race in races:
            qualified = list(filter(
                lambda x: race.is_qualified(x),
                horses.values()))
            weights = [math.ceil(x.quality) for x in qualified]
            s = sum(weights)
            weights = [x / s for x in weights]
            diff = 1 - sum(weights)
            if diff != 0 and len(weights) > 0:
                weights[-1] += diff
            if len(qualified) > 0:
                qualified_horses = list(
                    numpy.random.choice(qualified,
                                        min(race.max_horses, len(qualified)),
                                        replace=False,
                                        p=weights))
            else:
                qualified_horses = []
            race.horses = qualified_horses
            for horse in qualified_horses:
                horses.pop(horse.id)
        return horses

    async def generate_races(self):
        race_types = self.race_types
        start_time = self.start_time
        index = 1
        races = []
        maiden_races = []
        listed_races = []
        other_races = []
        for _ in range(race_types.maidens):
            race = self.create_maiden_race(start_time, index)
            index += 1
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.total_seconds()
            race.settings['restrict_time'] = delta.total_seconds() + 60 * 60
            race.settings['max_horses'] = 12
            races.append(race)
            maiden_races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        for _ in range(race_types.stakes):
            race = self.create_stake_race(start_time, index)
            index += 1
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.total_seconds()
            race.settings['restrict_time'] = delta.total_seconds() + 60 * 60
            race.settings['max_horses'] = 12
            races.append(race)
            other_races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        for _ in range(race_types.listed):
            race = self.create_listed_race(start_time, index)
            index += 1
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.total_seconds()
            race.settings['restrict_time'] = delta.total_seconds() + 60 * 60
            race.settings['max_horses'] = 12
            races.append(race)
            listed_races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        horses = self.stadium.unowned_qualified_horses()
        # Loop through maiden races
        self.prefill_races(maiden_races, horses)
        # Loop through listed races
        self.prefill_races_weighted(listed_races, horses)
        # Loop through other races
        self.prefill_races(other_races, horses)
        await self.stadium.bulk_add_races(races)
        for race in races:
            self.race_ids.append(race.id)

    async def manage_event(self):
        now = datetime.datetime.now().astimezone()
        if now >= self.announcement_time and self.phase == 0:
            await self.generate_races()
            await self.announce_event()
            return True
        elif now >= self.registration_time and self.phase == 1:
            for race in self.races:
                embed = discord.Embed(title='Building Race')
                placeholder = await self.channel.send(embed=embed)
                race.settings['message'] = placeholder
                race.can_run = True
                await race.save()
            self.phase += 1
            return True
        elif self.races_finished and self.phase >= 2:
            try:
                await self.close_event()
            except ValueError:
                return False
            else:
                return True
        return False

    def to_json(self):
        return {
            'name': self.name,
            'channel': self.channel.id,
            'race_ids': self.race_ids,
            'settings': self.settings
        }

    @classmethod
    def from_json(cls, stadium: 'Stadium', data: dict):
        event = cls(stadium, data['channel'], start_time=data['settings'],
                    races=RaceTypeCount())
        event.name = data['name']
        event.race_ids = data['race_ids']
        if isinstance(data['channel'], list):
            event.channel = Item.deserialize(data['channel'],
                                             bot=event.stadium.server.bot,
                                             guild=event.stadium.guild)
        else:
            event.channel = stadium.server.bot.get_channel(data['channel'])

        event.settings = data['settings']
        return event
