import datetime
import math
from typing import TYPE_CHECKING

import discord
import numpy

from .race import Race
from ..tools.settings import Item

if TYPE_CHECKING:
    from ..stadium import Stadium


class Event:
    def __init__(self, stadium: 'Stadium', channel: discord.TextChannel, *,
                 event_type: str = 'daily',
                 start_time: datetime.datetime,
                 betting_time: int = 60 * 60 * 1,
                 registration_time: int = 60 * 60 * 6,
                 announcement_time: int = 60 * 60 * 12,
                 races: int, ):
        self.name = 'Unnamed Event'
        self.stadium = stadium
        self.channel = channel
        self.race_ids = []
        self.settings = {
            'type': event_type,
            'start_time': start_time,
            'betting_time': betting_time,
            'registration_time': registration_time,
            'announcement_time': announcement_time,
            'races': races,
            'buffer': 5,
            'phase': 0,
            'winner_string': ''
        }

    @property
    def races(self):
        races = filter(lambda x: x.id in self.race_ids, self.stadium.races)
        races = list(sorted(races, key=lambda x: x.race_time))
        return races

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
    def betting_time(self):
        return (self.settings['start_time']
                - datetime.timedelta(seconds=self.settings['betting_time']))

    @property
    def registration_time(self):
        return (self.settings['start_time']
                - datetime.timedelta(
                    seconds=self.settings['registration_time']
                ))

    @property
    def announcement_time(self):
        return (self.settings['start_time']
                - datetime.timedelta(
                    seconds=self.settings['announcement_time']
                ))

    @property
    def races_finished(self):
        for race in self.races:
            if not race.finished:
                return False
        return True

    @classmethod
    def from_data(cls, stadium: 'Stadium', data: dict):
        event = cls(stadium, data['channel'], start_time=data['settings'],
                    races=4)
        event._deserialize(data)
        return event

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
        race.name = f'{self.name} Race {index}: Listed Stakes Race'
        race.settings['purse'] = 2000
        race.settings['stake'] = int(2000 * 0.05)
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
        self.stadium.events.remove(self)

    async def maidens_available(self):
        maidens = 0
        for horse in self.stadium.horses.values():
            is_maiden = horse.is_maiden()
            if is_maiden:
                maidens += 1
        return maidens

    async def generate_races(self):
        allowed_races = self.settings['races']
        maidens = await self.maidens_available()
        maiden_percentage = maidens / len(self.stadium.horses)
        maiden_races_allowed = maidens // 12
        if maiden_percentage > 0.5:
            maiden_races = allowed_races // 2
        else:
            maiden_races = allowed_races // 4
        if maiden_races > maiden_races_allowed:
            maiden_races = maiden_races_allowed

        horses = list(self.stadium.unowned_qualified_horses().values())
        stakes_qualified = list(filter(
            lambda x: Race.check_qualification('stake', x),
            self.stadium.horses.values()))
        listed_qualified = list(filter(
            lambda x: Race.check_qualification('listed', x),
            self.stadium.horses.values()))
        listed_races = min([len(listed_qualified) // 6, 1])
        stakes_races = min([len(stakes_qualified) // 6,
                            allowed_races - listed_races - maiden_races])

        start_time = self.settings['start_time']
        index = 1
        races = []
        for _ in range(maiden_races):
            race = self.create_maiden_race(start_time, index)
            index += 1
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.seconds
            race.settings['max_horses'] = 12
            races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        for _ in range(stakes_races):
            race = self.create_stake_race(start_time, index)
            index += 1
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.seconds
            races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        for _ in range(listed_races):
            race = self.create_listed_race(start_time, index)
            index += 1
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.seconds
            races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        used_horses = []
        for race in reversed(races):
            qualified = list(filter(
                lambda x: race.is_qualified(x) and x not in used_horses,
                horses))
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
            used_horses.extend(qualified_horses)
            race.horses = qualified_horses
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

    def serialize(self):
        return {
            'name': self.name,
            'channel': Item.serialize(self.channel),
            'race_ids': self.race_ids,
            'settings': Item.serialize_dict(self.settings)
        }

    def _deserialize(self, data: dict):
        self.name = data['name']
        self.channel = Item.deserialize(data['channel'],
                                        bot=self.stadium.server.bot,
                                        guild=self.stadium.guild)
        self.race_ids = data['race_ids']
        self.settings = Item.deserialize_dict(data['settings'],
                                              bot=self.stadium.server.bot,
                                              guild=self.stadium.guild)
