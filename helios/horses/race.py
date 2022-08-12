import asyncio
import datetime
import math
import random
from fractions import Fraction
from typing import Optional, TYPE_CHECKING, List, Dict

import discord

from .enumerations import BetType
from .horse import Horse
from .views import PreRaceView
from ..abc import HasSettings
from ..exceptions import IdMismatchError
from ..tools.settings import Item
from ..types.horses import MaxRaceHorses, RaceTypes
from ..types.settings import EventRaceSettings

if TYPE_CHECKING:
    from ..stadium import Stadium
    from ..member import HeliosMember


class Record:
    def __init__(self):
        self.id = 0
        self.horse_id = 0
        self.race_id = 0
        self.race_type = 'None'
        self.earnings = 0
        self.placing = 0
        self.date = datetime.datetime.now().astimezone().date()

    @classmethod
    def new(cls,
            horse: 'RaceHorse',
            event_race: 'Race',
            earnings: float):
        if not event_race.finished:
            raise ValueError('event_race must be finished')
        record = cls()
        record.id = 0
        record.horse_id = horse.horse.id
        record.race_id = event_race.id
        record.race_type = event_race.settings['type']
        record.earnings = earnings
        record.placing = event_race.race.finished_horses.index(horse)
        return record

    @classmethod
    def from_data(cls, data: dict):
        record = cls()
        record._deserialize(data)
        return record

    @property
    def is_new(self) -> bool:
        return self.id == 0

    def serialize(self):
        return {
            'id': self.id,
            'horse': self.horse_id,
            'race': self.race_id,
            'type': self.race_type,
            'earnings': self.earnings,
            'placing': self.placing,
            'date': self.date.isoformat()
        }

    def _deserialize(self, data: dict):
        self.id = data['id']
        self.horse_id = data['horse']
        self.race_id = data['race']
        self.race_type = data['type']
        self.earnings = data['earnings']
        self.placing = data['placing']
        self.date = datetime.date.fromisoformat(data['data'])


class Bet:
    def __init__(self, bet_type: BetType, horse_id: int, better_id: int,
                 amount: int):
        self.type = bet_type
        self.horse_id = horse_id
        self.better_id = better_id
        self.amount = amount
        self.amount_returned = 0
        self.fulfilled = False
        self.timestamp = datetime.datetime.now().astimezone()

    @classmethod
    def from_dict(cls, data):
        bet = cls(BetType(data['type']), data['horse_id'], data['better_id'],
                  data['amount'])
        bet.fulfilled = data['fulfilled']
        bet.amount_returned = data.get('amount_returned', 0)
        bet.timestamp = Item.deserialize(data['timestamp'])
        return bet

    def get_bet_result(self, finished_horses: List[Horse]) -> bool:
        finished_horse_ids = [x.id for x in finished_horses]
        if self.type is BetType.win:
            return self.horse_id in finished_horse_ids[:1]
        elif self.type is BetType.place:
            return self.horse_id in finished_horse_ids[:2]
        elif self.type is BetType.show:
            return self.horse_id in finished_horse_ids[:3]
        else:
            return False

    def serialize(self):
        return {
            'type': self.type.value,
            'horse_id': self.horse_id,
            'better_id': self.better_id,
            'amount': self.amount,
            'amount_returned': self.amount_returned,
            'fulfilled': self.fulfilled,
            'timestamp': Item.serialize(self.timestamp)
        }

    def _deserialize(self, data: dict):
        self.type = BetType(data['type'])
        self.horse_id = data['horse_id']
        self.better_id = data['better_id']
        self.amount = data['amount']
        self.fulfilled = data['fulfilled']
        self.timestamp = Item.deserialize(data['timestamp'])


class RaceHorse:
    SPEED_LIMITER_MULTIPLIER = 1
    BASE_SPEED = 10
    BASE_ACCEL = 3

    def __init__(self, horse: Horse, jockey=None):
        self.name = horse.name
        self.horse = horse
        self.jockey = jockey
        self.speed = 0
        self.progress = 0
        self.achieved_target = False
        self.stamina = horse.stamina
        self.tick_finished = None
        self.sub_tick_finished = 0  # In order of finish mid-tick

    @property
    def max_speed(self) -> float:
        max_speed = (RaceHorse.BASE_SPEED
                     + (self.horse.speed * 0.1)
                     * RaceHorse.SPEED_LIMITER_MULTIPLIER)
        min_max_speed = max_speed * 0.5
        diff = min_max_speed * self.stamina_percentage
        return round(min_max_speed + diff, 4)

    @property
    def speed_increase(self) -> float:
        return round(
            (RaceHorse.BASE_ACCEL + (self.horse.acceleration * 0.5))
            * 0.1 * RaceHorse.SPEED_LIMITER_MULTIPLIER, 4)

    @property
    def speed_percentage(self) -> float:
        return round(self.speed / self.max_speed, 4)

    @property
    def stamina_percentage(self) -> float:
        return round(self.stamina / self.horse.stamina, 4)

    def get_random_increase(self, variation: float):
        return random.uniform(self.speed_increase * (1 - variation),
                              self.speed_increase)

    def tick_speed(self):
        acceleration_variation = 0.2
        acceleration_multiplier = 1
        target = 0.8
        min_speed = 0.5
        # max_speed = 1
        if self.speed > self.max_speed:
            self.speed = self.max_speed

        if self.speed_percentage < min_speed:
            # Best increase
            self.speed += self.speed_increase
        elif not self.achieved_target:
            # Varied increase
            increase = round(self.get_random_increase(acceleration_variation),
                             4)
            self.speed += increase
            if self.speed_percentage >= target:
                self.achieved_target = True
        else:
            # Potential decrease
            if self.speed_percentage < target:
                # Chance to decrease when lower than target speed
                chance_to_decrease = 0.33
            elif self.speed_percentage > target:
                # Chance to decrease when faster than target speed
                chance_to_decrease = 0.66
            else:
                # Chance to decrease when matching target speed - Very
                # unlikely scenario
                chance_to_decrease = 0.5
            amt_to_change = acceleration_multiplier * self.speed_increase
            if random.random() > chance_to_decrease:
                self.speed += amt_to_change
            else:
                self.speed -= amt_to_change

        if self.speed > self.max_speed:
            self.speed = self.max_speed
        elif self.speed < 0:
            self.speed = 0
        return self.speed

    def tick_stamina(self):
        self.stamina -= self.speed
        if self.stamina < 0:
            self.stamina = 0

    def tick(self) -> float:
        self.progress += self.tick_speed()
        self.tick_stamina()
        return self.speed


class BasicRace:
    def __init__(self):
        self._id = 0
        self.horses: list[RaceHorse] = []
        self.finished_horses: list[RaceHorse] = []
        self.length = 500
        self.tick_number = 0
        self.phase = 0

    @property
    def finished(self) -> bool:
        return len(self.finished_horses) == len(self.horses)

    def tick(self):
        self.tick_number += 1
        to_finish = []
        for h in self.horses:
            if h.progress < self.length:
                h.tick()

            if h.progress >= self.length and h not in self.finished_horses:
                to_finish.append(h)

        # Sort based on time to finish using remaining distance / speed
        to_finish.sort(
            key=lambda x: (self.length - (x.progress - x.speed)) / x.speed)

        for i, h in enumerate(to_finish):
            h.tick_finished = self.tick_number
            h.sub_tick_finished = i
            self.finished_horses.append(h)

        self.finished_horses.sort(key=lambda x: (x.tick_finished,
                                                 x.sub_tick_finished))

        if len(self.finished_horses) >= len(self.horses) - 1:
            self.phase += 1
            if len(self.finished_horses) == len(self.horses) - 1:
                for h in self.horses:
                    if h not in self.finished_horses:
                        self.finished_horses.append(h)
                        break

    def set_horses(self, horses: list[Horse]):
        race_horses = []
        for h in horses:
            race_horses.append(RaceHorse(h))
        self.horses = race_horses

    def get_positions(self) -> list[RaceHorse]:
        progress_sort = sorted(self.horses, key=lambda rh: rh.progress,
                               reverse=True)
        final_list = [*self.finished_horses]
        for horse in progress_sort:
            if horse not in final_list:
                final_list.append(horse)
        return final_list

    def get_progress_string(self, size=10):
        total_size = size
        filled_char = '▰'
        empty_char = '▱'
        progress_string = ''
        position_sorted_list = self.get_positions()

        for h in self.horses:
            p = ''
            percent = (h.progress / self.length) * 100
            if percent > 100:
                percent = 100
            filled = int((percent / 100) * total_size)
            empty = int(total_size - filled)
            for _ in range(filled):
                p += filled_char
            for _ in range(empty):
                p += empty_char
            progress_string += f'{p} `{position_sorted_list.index(h) + 1:2} ' \
                               f'{percent:7.3f}%` - {h.name}\n'
        return progress_string


class Race(HasSettings):
    _default_settings: EventRaceSettings = {
        'channel': None,
        'message': None,
        'purse': 1000,
        'stake': 50,
        'max_horses': 6,
        'type': 'basic',
        'race_time': datetime.datetime.now().astimezone(),
        'betting_time': 5 * 60,
        'phase': 0
    }

    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self._id = 0
        self.name = ''
        self.race: Optional[BasicRace] = None
        self.horses: list[Horse] = []
        self.bets: List[Bet] = []

        self.settings: EventRaceSettings = Race._default_settings.copy()

        self._task = None

    @property
    def id(self):
        return self._id

    @property
    def is_new(self):
        return self._id == 0

    @property
    def finished(self) -> bool:
        return self.race and self.race.finished

    @property
    def purse(self) -> int:
        return self.settings['purse']

    @property
    def stake(self) -> int:
        return self.settings['stake']

    @property
    def max_horses(self) -> MaxRaceHorses:
        return self.settings['max_horses']

    @property
    def channel(self) -> Optional[discord.TextChannel]:
        return self.settings['channel']

    @property
    def message(self) -> Optional[discord.Message]:
        return self.settings['message']

    @property
    def thread(self) -> Optional[discord.Thread]:
        return self.channel.get_thread(self.message.id)

    @property
    def race_time(self) -> datetime.datetime:
        return self.settings['race_time']

    @property
    def betting_time(self) -> datetime.datetime:
        return self.race_time - datetime.timedelta(
            seconds=self.settings['betting_time'])

    @property
    def time_until_race(self) -> datetime.timedelta:
        now = datetime.datetime.now().astimezone()
        return self.race_time - now

    @property
    def time_until_betting(self) -> datetime.timedelta:
        return self.time_until_race - datetime.timedelta(
            seconds=self.settings['betting_time'])

    @property
    def phase(self):
        return self.settings['phase']

    @phase.setter
    def phase(self, value: int):
        self.settings['phase'] = value

    @classmethod
    def new(cls, stadium: 'Stadium', channel: discord.TextChannel,
            race_type: RaceTypes, race_time: datetime.datetime):
        erace = cls(stadium)
        erace.settings['channel'] = channel
        erace.settings['type'] = race_type
        erace.set_race_time(race_time)
        return erace

    @classmethod
    def from_dict(cls, stadium: 'Stadium', data):
        erace = cls(stadium)
        erace._deserialize(data)
        return erace

    def _get_registration_embed(self) -> discord.Embed:
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=self.name + ' Registration',
            description='Betting will commence '
                        f'<t:{int(self.betting_time.timestamp())}:R>'
        )
        return embed

    def _get_race_embed(self) -> discord.Embed:
        if not self.race:
            desc_string = f'The {self.name} is about to commence!'
        elif self.finished:
            desc_string = f'{self.race.finished_horses[0].name} ' \
                          f'has won the race!\n\n'
            for i, horse in enumerate(self.race.finished_horses, start=1):
                desc_string += (f'{i}. {horse.name} finished in '
                                f'**{horse.tick_finished}.'
                                f'{horse.sub_tick_finished:02}** Seconds\n')
        else:
            desc_string = self.race.get_progress_string(20)

        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title=self.name,
            description=desc_string
        )
        embed.add_field(
            name='Race Information',
            value=(
                f'Type: {self.settings["type"].capitalize()}\n'
                f'Horses: {self.max_horses}'
            )
        )
        horse_string = ''
        for h in self.horses:
            owner = h.settings['owner']
            odds = self.calculate_odds(h)
            odds_ratio = Fraction(odds).limit_denominator(10)
            if not owner:
                owner = self.stadium.owner
            else:
                owner = owner.member
            horse_string += (f'`{odds_ratio.numerator:3} to '
                             f'{odds_ratio.denominator:2}` | {h.name} - '
                             f'{owner.mention}\n')
        embed.add_field(name='Horses', value=horse_string)
        embed.set_footer(text=f'Tick: {self.race.tick_number}')

        return embed

    def get_betting_embed(self) -> discord.Embed:
        embed = discord.Embed(
            colour=discord.Colour.green(),
            title=self.name + ' Betting',
            description=(f'Betting is now available. Race begins '
                         f'<t:{int(self.settings["race_time"].timestamp())}'
                         f':R>')
        )
        horse_string = ''
        place_string = ''
        show_string = ''
        for h in self.horses:
            owner = h.settings['owner']
            odds = self.calculate_odds(h)
            place = self.get_horse_type_bets(BetType.place, h)
            show = self.get_horse_type_bets(BetType.show, h)
            odds_ratio = Fraction(odds).limit_denominator()
            if not owner:
                owner = self.stadium.owner
            else:
                owner = owner.member
            horse_string += (f'`{odds_ratio.numerator:3} to '
                             f'{odds_ratio.denominator:2}` | {h.name} - '
                             f'{owner.mention}\n')
            place_string += f'`{place:6,}` - {h.name}\n'
            show_string += f'`{show:6,}` - {h.name}\n'
        embed.add_field(name='Horses', value=horse_string)
        embed.add_field(name='Places', value=place_string)
        embed.add_field(name='Shows', value=show_string)
        return embed

    def inflate_bets(self, amt_to_inflate: int):
        horse_qualities = [x.quality for x in self.horses]
        sum_qualities = sum(horse_qualities)
        for i, h in enumerate(self.horses):
            quality_percent = horse_qualities[i] / sum_qualities
            amt_to_bet = amt_to_inflate * quality_percent
            self.bet(BetType.win, self.stadium.owner_member, h,
                     int(amt_to_bet))
            self.bet(BetType.place, self.stadium.owner_member, h,
                     int(amt_to_bet))
            self.bet(BetType.show, self.stadium.owner_member, h,
                     int(amt_to_bet))

    def get_total_bets(self) -> int:
        total = 0
        for bet in self.bets:
            total += bet.amount
        return total

    def get_total_type_bets(self, t: BetType) -> int:
        total = 0
        for bet in list(filter(lambda x: x.type == t, self.bets)):
            total += bet.amount
        return total

    def get_winning_type_bets(self, t: BetType) -> int:
        if not self.finished:
            return 0
        total = 0
        if t == BetType.win:
            horses = self.race.finished_horses[:1]
        elif t == BetType.place:
            horses = self.race.finished_horses[:2]
        else:  # t == BetType.show:
            horses = self.race.finished_horses[:3]
        horses = [x.horse.id for x in horses]
        for bet in list(filter(lambda x: x.type == t and x.horse_id in horses,
                               self.bets)):
            total += bet.amount
        return total

    def get_horse_type_bets(self, t: BetType, h: Horse) -> int:
        total = 0
        for bet in list(filter(lambda x: x.type == t and x.horse_id == h.id,
                               self.bets)):
            total += bet.amount
        return total

    def calculate_odds(self, h: Horse):
        total = self.get_total_type_bets(
            BetType.win) * 1  # For houses take if needed later
        horse_pool = self.get_horse_type_bets(BetType.win, h)
        if horse_pool == 0:
            horse_pool = 1
            total += 1
        diff = total - horse_pool
        odds = diff / horse_pool
        odds = math.floor(odds * 10) / 10
        return odds

    def calculate_pool_odds(self, t: BetType):
        total = self.get_total_type_bets(t)
        winning = self.get_winning_type_bets(t)
        diff = total - winning
        odds = diff / winning
        return math.floor(odds * 10) / 10

    def get_bet_payout_amount(self, bet: Bet) -> int:
        if not self.finished:
            return 0
        if bet.type == BetType.win:
            winning_horse = self.race.finished_horses[0].horse
            if bet.horse_id == winning_horse.id:
                odds = self.calculate_odds(winning_horse)
                winning = bet.amount * odds
                return int(winning) + bet.amount
            return 0
        else:
            won = bet.get_bet_result(
                [x.horse for x in self.race.finished_horses])

            if won:
                odds = self.calculate_pool_odds(bet.type)
                winning = bet.amount * odds
                return int(winning) + bet.amount
            return 0

    def is_running(self) -> bool:
        return self._task and not self._task.done()

    def create_run_task(self):
        if not self.is_running():
            self._task = self.stadium.server.bot.loop.create_task(self.run())
        else:
            print('This is bad')

    def bet(self, bet_type: BetType, member: 'HeliosMember', horse: 'Horse',
            amount: int):
        bets = list(filter(
            lambda x:
            x.type == bet_type and x.better_id == member.member.id
            and x.horse_id == horse.id,
            self.bets
        ))
        if len(bets) > 0:
            bets[0].amount += amount
        else:
            bet = Bet(bet_type, horse.id, member.member.id, amount)
            self.bets.append(bet)

    def find_horse(self, name: str) -> 'Horse':
        name = name.lower()
        for horse in self.horses:
            if horse.name.lower() == name:
                return horse

    def is_qualified(self, horse: 'Horse') -> bool:
        """
        Check whether a horse is eligible for this race.
        :param horse: The horse to check
        :return: Whether the horse is allowed to race.
        """
        f'{self.name} {horse.name}'
        return True

    def set_race_time(self, dt: datetime.datetime):
        self.settings['race_time'] = dt

    def generate_race(self) -> BasicRace:
        race = BasicRace()
        race.set_horses(self.horses)
        self.race = race
        return race

    def get_payout_structure(self) -> list[float]:
        if self.max_horses == 6:
            structure = [.6, .2, .13, .05, .01, .01]
        else:  # self.max_horses == 12:
            structure = [.6, .18, .1, .04]
            amount_to_spread = .01
            for _ in range(12 - len(structure)):
                structure.append(amount_to_spread)

        return structure

    def get_payout_amount(self, structure: list[float]) -> list[float]:
        payout = []
        for p in structure:
            payout.append(round(self.purse * p, 2))
        if sum(payout) < self.purse:
            payout[0] += self.purse - sum(payout)
        return payout

    async def payout_horses(self):
        payout = self.get_payout_amount(self.get_payout_structure())
        for i, h in enumerate(self.race.finished_horses):
            h.horse.pay(payout[i])
            record = Record.new(h, self, payout[i])
            await self.save_record(record)

    async def run(self):
        cont = True
        view = None
        last_tick = None
        await self.save()
        while cont:
            if self.phase == 0:
                if view is None:
                    view = PreRaceView(self)
                view.check_race_status()
                await self.send_or_edit_message(
                    embed=self._get_registration_embed(), view=view)
                if self.time_until_betting > datetime.timedelta(seconds=0):
                    wait_for = self.time_until_betting.seconds
                    await asyncio.sleep(wait_for)
                self.phase = 1
                await self.save()
            elif self.phase == 1:
                # Registration complete, commence betting
                if view is None:
                    view = PreRaceView(self)
                view.check_race_status()
                if len(self.bets) == 0:
                    self.inflate_bets(10000)
                    await self.save()
                await self.send_or_edit_message(embed=self.get_betting_embed(),
                                                view=view)
                if not self.thread:
                    await self.message.create_thread(
                        name=f'{self.name}-{self.race_time.strftime("%H:%M")}',
                        auto_archive_duration=60
                    )
                if self.time_until_race > datetime.timedelta(seconds=0):
                    wait_for = self.time_until_race.seconds
                    await asyncio.sleep(wait_for)
                self.phase = 2
                await self.save()
                view = None
            elif self.phase == 2:
                # RACE TIME
                if self.race is None:
                    self.generate_race()
                    await self.send_or_edit_message(
                        embed=self._get_race_embed())
                    await asyncio.sleep(5)
                if last_tick is None:
                    last_tick = datetime.datetime.now()

                diff = datetime.datetime.now() - last_tick
                seconds = int(diff.seconds)
                for _ in range(seconds):
                    if not self.race.finished:
                        self.race.tick()
                last_tick = datetime.datetime.now()
                await self.send_or_edit_message(embed=self._get_race_embed())

                if self.race.finished:
                    self.phase = 3
                await asyncio.sleep(1)
            elif self.phase == 3:
                # Race over, time to calculate winnings for racers and betters.
                tasks = []
                member_bets: Dict[discord.Member, List[Bet]] = {}
                for bet in self.bets:
                    amount = self.get_bet_payout_amount(bet)
                    member = self.stadium.server.members.get(bet.better_id)
                    bet.fulfilled = True
                    bet.amount_returned = amount
                    if member and not member.member.bot:
                        if member_bets.get(member.member):
                            member_bets.get(member.member).append(bet)
                        else:
                            member_bets[member.member] = [bet]
                        member.points += amount
                        tasks.append(member.save())
                await self.payout_horses()
                for h in self.horses:
                    tasks.append(h.save())
                if len(tasks) > 0:
                    await asyncio.wait(tasks)
                sends = []
                for mem, bets in member_bets.items():
                    if mem.bot:
                        continue
                    desc = ''
                    earned = 0
                    for bet in bets:
                        earned += bet.amount_returned - bet.amount
                        desc += (
                            f'You bet **{bet.amount:,}** for '
                            f'{self.stadium.horses[bet.horse_id].name} to '
                            f'{bet.type.name}.\n'
                            f'You received **{bet.amount_returned:,}**'
                        )
                        if bet.amount_returned > 0:
                            desc += (
                                f' ( **{bet.amount_returned - bet.amount:,}**'
                                f' + Your bet of **{bet.amount:,}** )\n'
                            )
                        else:
                            desc += '\n'

                    desc += f'\nTotal Earnings: **{earned:,}**\n'

                    if self.message:
                        desc += f'\n[Race Link]({self.message.jump_url})'
                    embed = discord.Embed(
                        colour=discord.Colour.green(),
                        title=f'{self.name} Bet Summary',
                        description=desc
                    )
                    horse_string = ''
                    for i, h in enumerate(self.race.finished_horses, start=1):
                        horse_string += f'{i}. {h.name}\n'
                    embed.add_field(name='Horse Placings', value=horse_string)
                    sends.append(mem.send(embed=embed))

                if len(sends) > 0:
                    await asyncio.wait(sends)

                self.phase = 4
                await self.save()
            else:
                # Everything is over. GG.
                self.stadium.races.remove(self)
                await self.stadium.save()
                cont = False

    async def send_or_edit_message(self, content=None, *, embed=None,
                                   view=None):
        if self.message is None:
            self.settings['message'] = await self.channel.send(content=content,
                                                               embed=embed,
                                                               view=view)
            await self.save()
        else:
            try:
                await self.message.edit(content=content, embed=embed,
                                        view=view)
            except discord.NotFound:
                self.settings['message'] = None
                await self.send_or_edit_message(content, embed=embed,
                                                view=view)

    async def save(self):
        if self.is_new:
            data = self.serialize()
            del data['id']
            resp = await self.stadium.server.bot.helios_http.post_race(data)
            self._id = resp['id']
        else:
            await self.stadium.server.bot.helios_http.patch_race(
                self.serialize())

    async def save_record(self, record: Record):
        if record.is_new:
            resp = await self.stadium.server.bot.helios_http.post_record(
                record.serialize()
            )
            record.id = resp['id']
        else:
            await self.stadium.server.bot.helios_http.patch_record(
                record.serialize()
            )

    def serialize(self):
        return {
            'id': self.id,
            'server': self.stadium.server.id,
            'name': self.name,
            'bets': [x.serialize() for x in self.bets],
            'horses': Item.serialize_list(self.horses),
            'settings': Item.serialize_dict(self.settings)
        }

    def _deserialize(self, data):
        if self.stadium.server.id != data['server']:
            raise IdMismatchError('This data does not belong to this server.')
        self._id = data['id']
        self.name = data['name']
        self.horses = Item.deserialize_list(data['horses'],
                                            guild=self.stadium.guild,
                                            bot=self.stadium.server.bot)
        self.bets = [Bet.from_dict(x) for x in data['bets']]
        settings = {**self._default_settings, **data['settings']}
        self.settings = Item.deserialize_dict(settings,
                                              guild=self.stadium.guild,
                                              bot=self.stadium.server.bot)
