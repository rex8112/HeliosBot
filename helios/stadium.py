import asyncio
import datetime
import random
from typing import TYPE_CHECKING, Optional, Dict, List

import discord

from .abc import HasSettings
from .exceptions import IdMismatchError
from .horses.horse import Horse
from .horses.race import EventRace
from .member import HeliosMember
from .tools.settings import Item
from .types.horses import StadiumSerializable
from .types.settings import StadiumSettings

if TYPE_CHECKING:
    from .server import Server


class Stadium(HasSettings):
    _default_settings: StadiumSettings = {
        'season': 0,
        'category': None,
        'announcement_id': 0
    }
    required_channels = [
        'announcements',
        'basic-races'
    ]
    epoch_day = datetime.datetime(2022, 8, 1, 1, 0, 0)
    daily_points = 100

    def __init__(self, server: 'Server'):
        self.server = server
        self.horses: dict[int, 'Horse'] = {}
        self.races: list['EventRace'] = []
        self.day = 0
        self.settings: StadiumSettings = self._default_settings.copy()

        self._running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def id(self) -> int:
        return self.server.id

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def guild(self) -> discord.Guild:
        return self.server.guild

    @property
    def owner(self) -> discord.Member:
        return self.guild.me

    @property
    def owner_member(self) -> 'HeliosMember':
        return HeliosMember(self.server.members, self.owner)

    @property
    def category(self) -> Optional[discord.CategoryChannel]:
        c = self.settings['category']
        if c:
            return c
        else:
            return None

    @property
    def announcement_channel(self) -> Optional[discord.TextChannel]:
        if self.category:
            return next(filter(lambda x: x.name == 'announcements', self.category.channels))

    @property
    def basic_channel(self) -> Optional[discord.TextChannel]:
        if self.category:
            return next(filter(lambda x: x.name == 'basic-races', self.category.channels))

    @staticmethod
    def get_day():
        epoch_day = Stadium.epoch_day
        delta = datetime.datetime.now() - epoch_day
        return delta.days

    def get_owner_horses(self, member: 'HeliosMember') -> Dict[int, 'Horse']:
        horses = filter(lambda h: h.owner == member, self.horses.values())
        horse_dict = {}
        for h in horses:
            horse_dict[h.id] = h
        return horse_dict

    def new_basic_race(self) -> bool:
        now = datetime.datetime.now().astimezone()
        next_slot = now + datetime.timedelta(minutes=15)
        next_slot = next_slot - datetime.timedelta(
            minutes=next_slot.minute % 15,
            seconds=next_slot.second,
            microseconds=next_slot.microsecond
        )
        delta = next_slot - now
        if delta.seconds < 360:
            next_slot = next_slot + datetime.timedelta(minutes=15)
        if self.basic_channel:
            er = EventRace.new(self, self.basic_channel, 'basic', next_slot)
            er.name = 'Quarter Hourly'
            er.settings['betting_time'] = 300
            er.horses = random.sample(list(self.horses.values()), k=er.max_horses)
            self.races.append(er)
            er.create_run_task()
            return True
        return False

    def serialize(self) -> StadiumSerializable:
        return {
            'server': self.server.id,
            'day': self.day,
            'settings': Item.serialize_dict(self.settings)
        }

    def _deserialize(self, data: StadiumSerializable):
        if data['server'] != self.server.id:
            raise IdMismatchError('This stadium does not belong to this server.')
        self.day = data['day']
        self.settings = Item.deserialize_dict(
            {**self._default_settings, **data['settings']},
            bot=self.server.bot,
            guild=self.guild
        )

    async def save(self, new=False):
        if new:
            await self.server.bot.helios_http.post_stadium(self.serialize())
        else:
            await self.server.bot.helios_http.patch_stadium(self.serialize())

    async def batch_create_horses(self, count: int):
        tasks = []
        used_names = [x.name for x in self.horses.values()]
        random_names = await self.server.bot.helios_http.request_names(count + 20)
        for _ in range(count):
            name = random_names[-1]
            random_names.pop()
            while name in used_names:
                name = random_names[-1]
                random_names.pop()

            h = Horse.new(self, name, 'Unknown', None)
            await h.save()
            self.horses[h.id] = h
            used_names.append(name)

    async def build_channels(self):
        category = self.category
        if category:
            for channel_name in self.required_channels:
                channels = list(filter(lambda x: x.name == channel_name, category.channels))
                if len(channels) > 0:
                    channel = channels[0]
                else:
                    channel = None
                if not channel:
                    await self.category.create_text_channel(channel_name)

    async def setup(self, data: StadiumSerializable = None):
        if data is None:
            data = await self.server.bot.helios_http.get_stadium(stadium_id=self.server.id)
        if data is None:
            await self.save(new=True)
        else:
            self._deserialize(data)
            horse_data: List[Dict] = await self.server.bot.helios_http.get_horse(server=self.server.id)
            for hdata in horse_data:
                h = Horse.from_dict(self, hdata)
                self.horses[h.id] = h

            race_data: List[Dict] = await self.server.bot.helios_http.get_race(server=self.server.id)
            for rdata in race_data:
                if rdata['settings']['phase'] >= 4:
                    continue
                else:
                    r = EventRace.from_dict(self, rdata)
                    self.races.append(r)
                    r.create_run_task()
        self.create_run_task()

    def create_run_task(self):
        if not self._task or self._task.done():
            self._task = self.server.bot.loop.create_task(self.run())

    async def run(self):
        self._running = True
        cont = True
        while cont:
            if self.category is None:
                cont = False
                break
            if self.settings['announcement_id'] == 0:
                await self.announcement_channel.send(
                    embed=self._get_new_stadium_embed()
                )
                self.settings['announcement_id'] = 1
            cur_day = self.get_day()
            if cur_day != self.day:
                self.day = cur_day
                # Check if horses need to be added to the pool
                if len(self.horses) < 100:
                    await self.batch_create_horses(100)
                    await self.save()

            # Ensure all races are still running and restart them if not
            for race in self.races:
                if not race.is_running():
                    race.create_run_task()

            basic_races = list(filter(lambda r: r.settings['type'] == 'basic',
                                      self.races))
            if len(basic_races) < 1:
                self.new_basic_race()
                await self.save()
            await asyncio.sleep(60)
        self._running = False

    def _get_new_stadium_embed(self) -> discord.Embed:
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title='Welcome to the Helios Stadium!',
            description=(
                'This is your one stop shop for anything horse racing. Want to bet on an unimportant but always '
                f'happening race? Head to {self.basic_channel.mention}. Low on cash? Try /daily. Be sure to hang out, '
                'upcoming features will use activity points which are now being accumulated via voice channels.'
            )
        )
        embed.add_field(
            name='Bet Types',
            value=(
                'In horse racing you are always betting against other bettors, not the house, therefore '
                'the odds of your bets are affected by the amount of other bets.\n\n'
                'Curious what win, place, and show mean? Let me explain:\n\n'
                '**Win**: This one is pretty self explanatory, you are betting on your horse to win first place '
                'in the race. Your payout is based on the listed odds on the betting screen at the time the race '
                'starts, not at the time of the bet.\n'
                '**Place**: You are betting on your horse getting either first or second place. The payout is usually '
                'much lower than a win bet because the winning pool is split amongst the bettors of the two horses '
                'in first and second. But depending on amounts bet, this could theoretically be higher.\n'
                '**Show**: This is nearly identical to a place bet except for first, second, and third positions.'
            ),
            inline=False
        )
        embed.add_field(
            name='Features to look forward to',
            value=(
                'In its current state, the Stadium allows for betting on Quarter Hourly races but that is not where it '
                'is going to end. There are many features planned for the Stadium, including but not limited to: '
                'Tournaments, Track Records, Horse and Jockey Ownership, and Horse Breeding.'
            )
        )
        return embed
