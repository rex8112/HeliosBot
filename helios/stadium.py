import asyncio
import datetime
from typing import TYPE_CHECKING, Optional, Dict, List, Tuple

import discord

from .abc import HasSettings
from .exceptions import IdMismatchError
from .horses.event import Event
from .horses.horse import Horse
from .horses.race import Race, Record
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
        'daily-events',
        'basic-races'
    ]
    epoch_day = datetime.datetime(2022, 8, 1, 1, 0, 0)
    daily_points = 100

    def __init__(self, server: 'Server'):
        self.server = server
        self.horses: dict[int, 'Horse'] = {}
        self.races: list['Race'] = []
        self.events: list['Event'] = []
        self.day = 0
        self.settings: StadiumSettings = self._default_settings.copy()

        self._running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def id(self) -> int:
        return self.server.id

    @property
    def event_race_ids(self) -> List[int]:
        ids = []
        for event in self.events:
            ids.extend(event.race_ids)
        return ids

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
            return next(filter(lambda x: x.name == 'announcements',
                               self.category.channels))

    @property
    def basic_channel(self) -> Optional[discord.TextChannel]:
        if self.category:
            return next(filter(lambda x: x.name == 'basic-races',
                               self.category.channels))

    @property
    def daily_channel(self) -> Optional[discord.TextChannel]:
        if self.category:
            return next(filter(lambda x: x.name == 'daily-events',
                               self.category.channels))

    @staticmethod
    def get_day():
        epoch_day = Stadium.epoch_day
        delta = datetime.datetime.now() - epoch_day
        return delta.days

    @staticmethod
    def get_win_loss(records: List[Record]) -> Tuple[int, int]:
        win = 0
        loss = 0
        for record in records:
            if record.placing == 0:
                win += 1
            else:
                loss += 1
        return win, loss

    @staticmethod
    def get_win_place_show_loss(records: List[Record]) -> Tuple[int, int, int,
                                                                int]:
        win = 0
        place = 0
        show = 0
        loss = 0
        for record in records:
            if record.placing == 0:
                win += 1
            elif record.placing == 1:
                place += 1
            elif record.placing == 2:
                show += 1
            else:
                loss += 1
        return win, place, show, loss

    @staticmethod
    def get_earnings(records: List[Record]) -> int:
        earnings = 0
        for record in records:
            earnings += record.earnings
        return earnings

    def unowned_horses(self) -> Dict[int, Horse]:
        horses = {}
        for key, horse in self.horses.items():
            if horse.owner is None:
                horses[key] = horse
        return horses

    def racing_horses(self) -> List[Horse]:
        horses = []
        for race in self.races:
            if race.phase < 4:
                horses.extend(race.horses)
        return horses

    def is_running(self) -> bool:
        if self._task:
            result = self._task.done()
            return not result
        return False

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
            er = Race.new(self, self.basic_channel, 'basic', next_slot)
            er.name = 'Quarter Hourly'
            er.settings['betting_time'] = 300
            self.races.append(er)
            er.create_run_task()
            return True
        return False

    def serialize(self) -> StadiumSerializable:
        return {
            'server': self.server.id,
            'day': self.day,
            'settings': Item.serialize_dict(self.settings),
            'events': [x.serialize() for x in self.events]
        }

    def _deserialize(self, data: StadiumSerializable):
        if data['server'] != self.server.id:
            raise IdMismatchError(
                'This stadium does not belong to this server.')
        self.day = data['day']
        self.settings = Item.deserialize_dict(
            {**self._default_settings, **data['settings']},
            bot=self.server.bot,
            guild=self.guild
        )
        self.events = [Event.from_data(self, x) for x in data['events']]

    async def add_race(self, race: 'Race'):
        self.races.append(race)
        await race.save()
        await self.save()

    async def bulk_add_races(self, races: List['Race']):
        data = [x.serialize() for x in races]
        tasks = []
        for race in races:
            self.races.append(race)
            tasks.append(race.save())
        tasks.append(self.save())
        await asyncio.wait(tasks)

    async def save(self, new=False):
        if new:
            await self.server.bot.helios_http.post_stadium(self.serialize())
        else:
            await self.server.bot.helios_http.patch_stadium(self.serialize())

    async def batch_create_horses(self, count: int):
        tasks = []
        used_names = [x.name for x in self.horses.values()]
        random_names = await self.server.bot.helios_http.request_names(
            count * 2)
        for _ in range(count):
            name = random_names[-1]
            random_names.pop()
            while name in used_names:
                name = random_names[-1]
                random_names.pop()

            used_names.append(name)
            h = Horse.new(self, name, 'Unknown', None)
            await h.save()
            self.horses[h.id] = h
            used_names.append(name)

    async def build_records(self, *, horse: 'Horse' = None,
                            allow_basic: bool = False,
                            after: Optional[datetime.datetime] = None) -> Dict[
                            int, List[Record]]:
        params = {}
        if horse:
            params['horse'] = horse.id
        if allow_basic:
            params['basic'] = 1
        if after:
            params['after'] = after.isoformat()
        resp = await self.server.bot.helios_http.get_record(**params)
        records = {}
        for data in resp:
            record = Record.from_data(data)
            if records.get(record.horse_id):
                records[record.horse_id].append(record)
            else:
                records[record.horse_id] = [record]
        for h in self.horses.values():
            recs = records.get(h.id, list())
            if h.get_flag('QUALIFIED') and horse is None:
                recs = list(filter(lambda r: r.race_type != 'basic', recs))
            h.records = recs
        return records

    async def build_channels(self):
        category = self.category
        if category:
            for channel_name in self.required_channels:
                channels = list(filter(lambda x: x.name == channel_name,
                                       category.channels))
                if len(channels) > 0:
                    channel = channels[0]
                else:
                    channel = None
                if not channel:
                    await self.category.create_text_channel(channel_name)

    async def setup(self, data: StadiumSerializable = None):
        if data is None:
            data = await self.server.bot.helios_http.get_stadium(
                stadium_id=self.server.id)
        if data is None:
            await self.save(new=True)
        else:
            self._deserialize(data)
            horse_data: List[
                Dict] = await self.server.bot.helios_http.get_horse(
                server=self.server.id)
            for hdata in horse_data:
                h = Horse.from_dict(self, hdata)
                self.horses[h.id] = h

            race_data: List[Dict] = await self.server.bot.helios_http.get_race(
                server=self.server.id)
            for rdata in race_data:
                if (rdata['settings']['phase'] >= 4
                        and rdata['id'] not in self.event_race_ids):
                    continue
                else:
                    r = Race.from_dict(self, rdata)
                    self.races.append(r)
                    r.create_run_task()
        await self.build_records(allow_basic=True)
        await self.build_channels()
        self.create_run_task()

    def create_run_task(self):
        if not self.is_running():
            self._task = self.server.bot.loop.create_task(self.run())

    async def run(self):
        self._running = True
        cont = True
        while cont:
            changed = False
            if self.category is None:
                cont = False
                break
            await self.manage_announcements()
            cur_day = self.get_day()
            if cur_day != self.day:
                self.day = cur_day
                # Check if horses need to be added to the pool
                unqualified_horses = list(filter(
                    lambda x: not x.get_flag('QUALIFIED'),
                    self.horses.values()))
                need_horses = 100 - len(unqualified_horses)
                if need_horses > 0:
                    await self.batch_create_horses(need_horses)
                    changed = True

            daily_events = list(filter(lambda e: e.settings['type'] == 'daily',
                                       self.events))
            if len(daily_events) < 1:
                now = datetime.datetime.now().astimezone()
                start_time = now.replace(hour=21, minute=0, second=0,
                                         microsecond=0)
                if now + datetime.timedelta(hours=1) >= start_time:
                    start_time += datetime.timedelta(days=1)

                new_event = Event(self, self.daily_channel,
                                  event_type='daily',
                                  start_time=start_time,
                                  races=6)
                new_event.name = f'{start_time.strftime("%A")} Daily Event'
                self.events.append(new_event)
                changed = True

            for event in self.events:
                result = await event.manage_event()
                if result:
                    changed = True

            # Ensure all races are still running and restart them if not
            for race in self.races:
                if not race.is_running():
                    race.create_run_task()

            basic_races = list(filter(lambda r: r.settings['type'] == 'basic',
                                      self.races))
            if len(basic_races) < 1:
                self.new_basic_race()
                changed = True
            if changed:
                await self.save()
            await asyncio.sleep(60)
        self._running = False

    async def manage_announcements(self):
        if self.settings['announcement_id'] == 0:
            await self.announcement_channel.send(
                embed=self._get_new_stadium_embed()
            )
            self.settings['announcement_id'] = 2
        elif self.settings['announcement_id'] == 1:
            embed = discord.Embed(
                colour=discord.Colour.orange(),
                title='Daily Events Release',
                description=(
                    'What are events? An event is a series of important races '
                    'that occur in quick succession. These races require '
                    'specific qualifications in order to race and also draw in'
                    ' more bets. While an event means less until horse '
                    'ownership is implemented, this can still affect you '
                    'greatly as once horses start winning races in the events '
                    'they will no longer show up in quarter hourly races.\n'
                    'Registration and Betting occur at the same time for every'
                    ' race in the event. Registration opens up six hours early'
                    ' at <t:1659384000:t>. Betting opens up an hour early at '
                    '<t:1659402000:t>. The races begin at <t:1659405600:t>.'
                )
            )
            embed.add_field(
                name='How Horses Qualify',
                value=(
                    'Events currently only consist of three possible races: '
                    '**Maiden, Stakes, and Listed Grade Stakes**. Each type'
                    'comes with better rewards for the horses, respectively.\n'
                    '**Maiden**: These races are the most simple race. Horses '
                    'who have never won an event race can race in a Maiden '
                    'race. However, to prevent flooding from new horses, a '
                    'horse must have earned 300 points from Quarter Hourly '
                    'races before they are considered eligible.\n'
                    '**Stakes**: These races are for any horse who have won '
                    'at least once, it does not matter if this was a Quarter '
                    'Hourly race or a Maiden race.\n'
                    '**Listed Grade Stakes**: The first tier of Graded Stakes.'
                    ' To qualify for this race, you must have won any single '
                    'event race, whether it be Maiden or Stakes. '
                    'Coincidentally, if a horse qualifies for a Listed race '
                    'it can no longer qualify for a Quarter Hourly.'
                )
            )
            await self.announcement_channel.send(
                embed=embed
            )
            self.settings['announcement_id'] = 2

    def _get_new_stadium_embed(self) -> discord.Embed:
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title='Welcome to the Helios Stadium!',
            description=(
                'This is your one stop shop for anything horse racing. Want to'
                ' bet on an unimportant but always '
                f'happening race? Head to {self.basic_channel.mention}. Low on'
                ' cash? Try /daily. Be sure to hang out, '
                'upcoming features will use activity points which are now '
                'being accumulated via voice channels. Be sure to check out '
                f'{self.daily_channel.mention} for Daily Events.'
            )
        )
        embed.add_field(
            name='Bet Types',
            value=(
                'In horse racing you are always betting against other bettors,'
                ' not the house, therefore '
                'the odds of your bets are affected by the amount of other '
                'bets.\n\n'
                'Curious what win, place, and show mean? Let me explain:\n\n'
                '**Win**: This one is pretty self explanatory, you are betting'
                ' on your horse to win first place '
                'in the race. Your payout is based on the listed odds on the '
                'betting screen at the time the race '
                'starts, not at the time of the bet.\n'
                '**Place**: You are betting on your horse getting either first'
                ' or second place. The payout is usually '
                'much lower than a win bet because the winning pool is split '
                'amongst the bettors of the two horses '
                'in first and second. But depending on amounts bet, this could'
                ' theoretically be higher.\n'
                '**Show**: This is nearly identical to a place bet except for '
                'first, second, and third positions.'
            ),
            inline=False
        )
        embed.add_field(
            name='Event Races',
            value=(
                'Events currently only consist of three possible races: '
                '**Maiden, Stakes, and Listed Grade Stakes**. Each type'
                'comes with better rewards for the horses, respectively.\n'
                '**Maiden**: These races are the most simple race. Horses '
                'who have never won an event race can race in a Maiden '
                'race. However, to prevent flooding from new horses, a '
                'horse must have earned 300 points from Quarter Hourly '
                'races before they are considered eligible.\n'
                '**Stakes**: These races are for any horse who have won '
                'at least once, it does not matter if this was a Quarter '
                'Hourly race or a Maiden race.\n'
                '**Listed Grade Stakes**: The first tier of Graded Stakes.'
                ' To qualify for this race, you must have won any single '
                'event race, whether it be Maiden or Stakes. '
                'Coincidentally, if a horse qualifies for a Listed race '
                'it can no longer qualify for a Quarter Hourly.'
            )
        )
        embed.add_field(
            name='Features to look forward to',
            value=(
                'In its current state, the Stadium allows for betting on '
                'Quarter Hourly races but that is not where it '
                'is going to end. There are many features planned for the '
                'Stadium, including but not limited to '
                'Horse and Jockey Ownership, '
                'and Horse Breeding.'
            )
        )
        return embed
