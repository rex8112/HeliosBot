import datetime
from typing import TYPE_CHECKING

import discord

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
        return race

    def create_stake_race(self, race_time: datetime.datetime, index):
        race = Race.new(self.stadium, self.channel, 'stake', race_time)
        race.can_run = False
        race.name = f'{self.name} Race {index}: Stakes Race'
        return race

    def create_listed_race(self, race_time: datetime.datetime, index):
        race = Race.new(self.stadium, self.channel, 'listed', race_time)
        race.can_run = False
        race.name = f'{self.name} Race {index}: Listed Stakes Race'
        return race

    async def announce_event(self):
        schedule_string = ''
        for race in self.races:
            start_time = race.race_time
            schedule_string += (f'<t:{int(start_time.timestamp())}:t> - '
                                f'{race.max_horses} Horse {race.name}\n')
        embed = discord.Embed(
            colour=discord.Colour.blue(),
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
            title=f'{self.name} has Ended!',
            description=('Congratulate our winners!\n\n'
                         f'{self.settings["winner_string"]}')
        )
        await self.channel.send(embed=embed)
        for race in self.races:
            self.stadium.races.remove(race)
        self.stadium.events.remove(self)

    async def maidens_available(self):
        records = await self.stadium.build_records(allow_basic=True)
        maidens = 0
        for h_id, record_list in records.items():
            is_maiden = True
            for record in record_list:
                if record.placing == 0:
                    is_maiden = False
                    break
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

        for _ in range(allowed_races - maiden_races - 1):
            race = self.create_stake_race(start_time, index)
            index += 1
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.seconds
            races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        for _ in range(allowed_races - len(races)):
            race = self.create_listed_race(start_time, index)
            index += 1
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.seconds
            races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

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
        elif self.races_finished:
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
