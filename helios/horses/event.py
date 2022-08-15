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
            'phase': 0
        }

    @property
    def races(self):
        races = list(filter(lambda x: x.id in self.race_ids,
                            self.stadium.races))
        return races

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

    def create_maiden_race(self, race_time: datetime.datetime):
        race = Race.new(self.stadium, self.channel, 'maiden', race_time)
        race.settings['can_run'] = False
        race.name = f'{self.name} Race {len(self.race_ids) + 1}: Maiden Race'
        return race

    def create_interim_race(self, race_time: datetime.datetime):
        race = Race.new(self.stadium, self.channel, 'interim', race_time)
        race.settings['can_run'] = False
        race.name = f'{self.name} Race {len(self.race_ids) + 1}: Interim Race'
        return race

    def create_stake_race(self, race_time: datetime.datetime):
        race = Race.new(self.stadium, self.channel, 'stake', race_time)
        race.settings['can_run'] = False
        race.name = f'{self.name} Race {len(self.race_ids) + 1}: Stakes Race'
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
        races = []
        for _ in range(maiden_races):
            race = self.create_maiden_race(start_time)
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.seconds
            races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        for _ in range(allowed_races - maiden_races - 1):
            race = self.create_interim_race(start_time)
            delta = start_time - self.betting_time
            race.settings['betting_time'] = delta.seconds
            races.append(race)
            start_time = start_time + datetime.timedelta(
                minutes=self.settings['buffer'])

        for _ in range(allowed_races - len(races)):
            race = self.create_stake_race(start_time)
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
        if self.phase > 1:
            return False
        if now >= self.announcement_time and self.phase == 0:
            await self.generate_races()
            await self.announce_event()
            return True
        elif now >= self.registration_time and self.phase == 1:
            for race in self.races:
                race.can_run = True
            self.phase += 1
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
