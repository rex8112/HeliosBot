import asyncio
import datetime
import math
import random
from fractions import Fraction
from typing import Optional, TYPE_CHECKING, List, Dict

import discord
from discord.utils import MISSING

from .enumerations import BetType
from .horse import Horse
from .views import PreRaceView
from ..abc import HasSettings
from ..exceptions import IdMismatchError
from ..tools.settings import Item
from ..types.horses import MaxRaceHorses, RaceTypes
from ..types.settings import RaceSettings

if TYPE_CHECKING:
    from .event import Event
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
        self.points = 0
        self.date = datetime.datetime.now().astimezone().date()

    @classmethod
    def new(cls,
            horse: 'RaceHorse',
            event_race: 'Race',
            earnings: float,
            points: int = 0):
        if not event_race.finished:
            raise ValueError('event_race must be finished')
        record = cls()
        record.id = 0
        record.horse_id = horse.horse.id
        record.race_id = event_race.id
        record.race_type = event_race.settings['type']
        record.earnings = int(earnings)
        record.points = points
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
            'points': self.points,
            'date': self.date.isoformat()
        }

    def _deserialize(self, data: dict):
        self.id = data['id']
        self.horse_id = data['horse']
        self.race_id = data['race']
        self.race_type = data['type']
        self.earnings = data['earnings']
        self.placing = data['placing']
        self.points = data.get('points', 0)
        self.date = datetime.date.fromisoformat(data['date'])


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
        for h in self.horses:
            if h.progress < self.length:
                h.tick()

            if h.progress >= self.length and h not in self.finished_horses:
                h.tick_finished = self.tick_number
                h.sub_tick_finished = ((self.length - (h.progress - h.speed))
                                       / h.speed)
                self.finished_horses.append(h)

        self.finished_horses.sort(key=lambda x: (x.tick_finished
                                                 + x.sub_tick_finished))

        if len(self.finished_horses) >= len(self.horses):
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
    _default_settings: RaceSettings = {
        'channel': None,
        'message': None,
        'purse': 1000,
        'stake': 50,
        'max_horses': 6,
        'type': 'basic',
        'race_time': datetime.datetime.now().astimezone(),
        'betting_time': 5 * 60,
        'restrict_time': 5 * 60,
        'phase': 0,
        'can_run': True,
        'invite_only': False
    }

    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self._id = 0
        self.name = ''
        self.race: Optional[BasicRace] = None
        self.horses: list[Horse] = []
        self.bets: List[Bet] = []
        self.settings: RaceSettings = Race._default_settings.copy()

        self.skip = False

        self._can_run_event = asyncio.Event()
        self._can_run_event.set()  # Start true like setting

        self._view = None
        self._task = None

    @property
    def id(self):
        return self._id

    @property
    def is_new(self):
        return self._id == 0

    @property
    def type(self) -> RaceTypes:
        return self.settings['type']

    @property
    def can_run(self):
        return self.settings['can_run']

    @can_run.setter
    def can_run(self, value: bool):
        self.settings['can_run'] = value
        if value:
            self._can_run_event.set()
        else:
            self._can_run_event.clear()

    @property
    def finished(self) -> bool:
        return (self.race and self.race.finished) or self.phase == 4

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
    def restrict_time(self) -> datetime.datetime:
        duration = datetime.timedelta(seconds=self.settings['restrict_time'])
        return self.race_time - duration

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

    @property
    def invite_only(self):
        return self.settings['invite_only']

    @invite_only.setter
    def invite_only(self, value: bool):
        self.settings['invite_only'] = value

    @property
    def event(self) -> Optional['Event']:
        for e in self.stadium.events.events:
            if self.id in e.race_ids:
                return e
        return None

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

    def get_registration_embed(self) -> discord.Embed:
        payout_structure = self.get_payout_structure()
        payout_structure = [f'{x:.0%}' for x in payout_structure]
        payout_structure = ', '.join(payout_structure)
        if self.settings['betting_time'] >= self.settings['restrict_time']:
            restriction = ''
        else:
            restriction = (f'Restrictions end '
                           f'<t:{int(self.restrict_time.timestamp())}:R>')
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=self.name + ' Registration',
            description='Betting will commence '
                        f'<t:{int(self.betting_time.timestamp())}:R>\n\n'
                        f'Purse: **{self.purse:,}**\n'
                        f'Stake to Enter: **{self.stake:,}**\n'
                        f'Payout: {payout_structure}\n\n'
                        f'Available Slots: {self.slots_left()}/'
                        f'{self.max_horses}\n\n'
                        f'{restriction}'
        )
        return embed

    def _get_invite_only_embed(self) -> discord.Embed:
        horse_string = self.horse_list_string()
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f'{self.name} Lineup',
            description=f'{horse_string}\nBetting will commence '
                        f'<t:{int(self.betting_time.timestamp())}:R>\n\n'
                        f'Purse: **{self.purse:,}**\n'
        )
        return embed

    def _get_race_embed(self) -> discord.Embed:
        if not self.race:
            desc_string = f'The {self.name} is about to commence!'
        elif self.finished:
            desc_string = f'{self.race.finished_horses[0].name} ' \
                          f'has won the race!\n\n'
            for i, horse in enumerate(self.race.finished_horses, start=1):
                desc_string += (
                    f'{i}. {horse.name} finished in '
                    f'**{horse.tick_finished + horse.sub_tick_finished:7.3f}'
                    f'** Seconds\n')
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
                f'Purse: {self.settings["purse"]:,}\n'
                f'Horses: {self.max_horses}'
            )
        )
        embed.add_field(name='Horses',
                        value=self.horse_list_string(show_odds=True))
        if self.skip:
            embed.set_footer(text=f'This race was skipped to ease rate limits')

        return embed

    def get_betting_embed(self) -> discord.Embed:
        embed = discord.Embed(
            colour=discord.Colour.green(),
            title=self.name + ' Betting',
            description=(f'Betting is now available. Race begins '
                         f'<t:{int(self.settings["race_time"].timestamp())}'
                         f':R>')
        )
        place_string = ''
        show_string = ''
        for i, h in enumerate(self.horses, start=1):
            place = self.get_horse_type_bets(BetType.place, h)
            show = self.get_horse_type_bets(BetType.show, h)
            place_string += f'`{place:6,}` - #{i} {h.name}\n'
            show_string += f'`{show:6,}` - #{i} {h.name}\n'
        embed.add_field(name='Horses',
                        value=self.horse_list_string(show_odds=True,
                                                     show_wr=True),
                        inline=False)
        embed.add_field(name='Places', value=place_string)
        embed.add_field(name='Shows', value=show_string)
        return embed

    def horse_list_string(self, *, show_odds=False, show_owner=True,
                          show_wr=False):
        horse_string = ''
        for i, h in enumerate(self.horses, start=1):
            owner = h.owner
            if not owner:
                owner = self.stadium.owner
            else:
                owner = owner.member
            if show_odds:
                odds = self.calculate_odds(h)
                odds_ratio = Fraction(odds).limit_denominator()
                horse_string += (f'`{odds_ratio.numerator:3} to '
                                 f'{odds_ratio.denominator:2}` | ')
            horse_string += f'#{i} {h.name}'
            if show_owner:
                horse_string += (' - '
                                 f'{owner.mention}')
            if show_wr:
                win, loss = self.stadium.get_win_loss(h.records)
                horse_string += f' - {win}/{loss}'
            horse_string += '\n'
        return horse_string

    def inflate_bets(self, amt_to_inflate: int):
        multipliers = [10, 8, 8, 7, 7, 7, 6, 6, 6, 6, 6, 6]
        horse_qualities = []
        for h in self.horses:
            horse_qualities.append((h, h.quality))
        sorted_horse_qualities = sorted(horse_qualities,
                                        key=lambda h_q: h_q[1],
                                        reverse=True)
        horses = [x[0] for x in sorted_horse_qualities]
        qualities = [x[1] for x in sorted_horse_qualities]
        minimum = min(qualities) - 10
        qualities = [x - minimum for x in qualities]
        horse_sum = sum(qualities)

        new_qualities = []
        for i, q in enumerate(qualities):
            p = q / horse_sum
            new_qualities.append(p)
        sum_qualities = sum(new_qualities)

        for i, h in enumerate(horses):
            quality_percent = new_qualities[i] / sum_qualities
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
        if winning <= 0:
            winning = 1
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

    def is_restricted(self) -> bool:
        now = datetime.datetime.now().astimezone()
        return now < self.restrict_time

    def is_running(self) -> bool:
        if self._task:
            result = self._task.done()
            return not result
        return False

    def create_run_task(self):
        if not self.is_running() and self.phase < 4:
            self._task = self.stadium.server.bot.loop.create_task(self.run())

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

    def slots_left(self):
        left = self.max_horses
        for horse in self.horses:
            if horse.owner is not None:
                left -= 1
        return left

    def find_horse(self, name: str) -> 'Horse':
        name = name.lower()
        for horse in self.horses:
            if horse.name.lower() == name:
                return horse

    def is_qualified(self, horse: 'Horse') -> bool:
        """
        Shortcut for Race.check_qualification while also checking for event
        doubling
        :param horse: The horse to check
        :return: Whether the horse is allowed to race.
        """
        # Prevent doubling up
        if horse in self.stadium.racing_horses():
            return False

        return self.stadium.check_qualification(self.settings['type'], horse)

    def set_race_time(self, dt: datetime.datetime):
        self.settings['race_time'] = dt

    def generate_race(self) -> BasicRace:
        race = BasicRace()
        race.set_horses(self.horses)
        self.race = race
        return race

    def get_payout_structure(self) -> list[float]:
        structure = [.6, .2, .1, .05, .025]
        remainder = 0.025
        remainder_horses = self.max_horses - 5
        if remainder_horses > 0:
            per_horse = remainder / remainder_horses
            per_horse = math.floor(per_horse * 10000) / 10000
            per_horse = round(per_horse, 4)
            for _ in range(remainder_horses):
                structure.append(per_horse)
        return structure

    def get_payout_amount(self, structure: list[float]) -> list[float]:
        payout = []
        for p in structure:
            payout.append(round(self.purse * p, 2))
        if sum(payout) < self.purse:
            payout[0] += round(self.purse - sum(payout), 2)
        return payout

    async def add_horse(self, horse: 'Horse'):
        if len(self.horses) < self.max_horses:
            self.horses.append(horse)
        else:
            index_to_pop = None
            for i, h in enumerate(self.horses):
                if h.owner is None:
                    index_to_pop = i
                    break
            if index_to_pop is None:
                raise IndexError('No available room for horse')
            self.horses.pop(index_to_pop)
            self.horses.append(horse)
        await self.save()

    async def payout_horses(self):
        payout = self.get_payout_amount(self.get_payout_structure())
        for i, h in enumerate(self.race.finished_horses):
            h.horse.pay(payout[i])
            record = Record.new(h, self, payout[i])
            h.horse.records.append(record)
            if record.race_type in ('maiden', 'stake') and record.placing == 0:
                h.horse.set_flag('MAIDEN', False)
                await h.horse.save()
            if (record.race_type in ('grade3', 'grade2', 'grade1')
                    and record.placing < 4):
                point_payout = [30, 4, 2, 1]
                record.points = point_payout[record.placing]
            await self.save_record(record)

            owner = h.horse.owner
            if owner:
                await owner.save()
                embed = discord.Embed(
                    colour=discord.Colour.orange(),
                    title=f'{h.horse.name} Race Results',
                    description=(
                        f'[{self.name}]({self.message.jump_url})\n'
                        f'Placed Position: {i + 1}\n'
                        f'Earnings: **{payout[i]:,}**\n'
                        f'Profit: **{payout[i] - self.stake:,}**'
                    )
                )
                try:
                    await owner.member.send(embed=embed)
                except (discord.HTTPException, discord.Forbidden,
                        discord.NotFound):
                    ...

    async def cancel(self):
        self.phase = 4
        embed = discord.Embed(
            colour=discord.Colour.red(),
            title=f'{self.name} Cancelled',
            description=(f'This race only had {len(self.horses)} horses '
                         'available to race and so it will not be finished. '
                         'All stakes have been paid back.')
        )
        for horse in self.horses:
            if horse.owner:
                horse.owner.points += self.stake
                await horse.owner.save()
        await self.send_or_edit_message(embed=embed)
        await self.save()

    async def run(self):
        cont = True
        last_tick = None
        if self.phase != 3:
            await self.save()
        await self._can_run_event.wait()
        while cont:
            if self.phase == 0:
                if self._view is None:
                    self._view = PreRaceView(self)
                self._view.check_race_status()
                if self.invite_only:
                    embed = self._get_invite_only_embed()
                else:
                    embed = self.get_registration_embed()
                await self.send_or_edit_message(
                    embed=embed, view=self._view)

                if not self.thread:
                    if self.settings['type'] == 'basic':
                        thread_time = 60
                    else:
                        thread_time = 1440
                    try:
                        await self.message.create_thread(
                            name=f'{self.name}-{self.race_time.strftime("%H:%M")}',
                            auto_archive_duration=thread_time
                        )
                    except discord.HTTPException:
                        ...

                if self.time_until_betting > datetime.timedelta(seconds=0):
                    wait_for = self.time_until_betting.total_seconds()
                    if wait_for > 0:
                        await asyncio.sleep(wait_for)

                remaining_horses = self.max_horses - len(self.horses)
                if remaining_horses > 0:
                    delta = self.max_horses - len(self.horses)
                    horses = list(
                        filter(lambda x: self.is_qualified(x),
                               self.stadium.unowned_qualified_horses().values()))
                    new_horses = random.sample(
                        horses,
                        k=min([delta, len(horses)]))
                    for h in new_horses:
                        self.horses.append(h)
                    # If there were not enough qualified horses, say fuck it
                    if len(self.horses) < self.max_horses // 2:
                        await self.cancel()
                        break
                self.phase = 1
                await self.save()
            elif self.phase == 1:
                # Registration complete, commence betting
                if self._view is None:
                    self._view = PreRaceView(self)
                self._view.check_race_status()
                if len(self.bets) == 0:
                    t = self.settings['type']
                    if t == 'maiden':
                        amt = 20_000
                    elif t == 'stake':
                        amt = 30_000
                    elif t == 'listed':
                        amt = 40_000
                    else:
                        amt = 10_000
                    self.inflate_bets(amt)
                    await self.save()
                await self.send_or_edit_message(embed=self.get_betting_embed(),
                                                view=self._view)
                if self.time_until_race > datetime.timedelta(seconds=0):
                    wait_for = self.time_until_race.total_seconds()
                    if wait_for > 0:
                        await asyncio.sleep(wait_for)
                self.phase = 2
                await self.save()
                self._view = None
            elif self.phase == 2:
                # RACE TIME
                if self.race is None:
                    self.generate_race()
                    await self.send_or_edit_message(
                        embed=self._get_race_embed(),
                        view=None
                    )
                    await asyncio.sleep(3)
                if last_tick is None:
                    last_tick = datetime.datetime.now()

                diff = datetime.datetime.now() - last_tick
                seconds = int(diff.seconds)
                if self.skip:
                    seconds = 120
                for _ in range(seconds):
                    if not self.race.finished:
                        self.race.tick()
                    else:
                        break
                last_tick = datetime.datetime.now()
                await self.send_or_edit_message(embed=self._get_race_embed(),
                                                view=None)

                if self.race.finished:
                    self.phase = 3
                    event = self.event
                    if event:
                        winner = self.race.finished_horses[0]
                        event.settings['winner_string'] += (
                            f'{self.name.replace(event.name, "")}: '
                            f'**{winner.name}**\n')
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
                if not self.event:
                    self.stadium.races.remove(self)
                    await self.stadium.save()
                cont = False

    async def update_embed(self):
        if self.phase == 0:
            embed = self.get_registration_embed()
        elif self.phase == 1:
            embed = self.get_betting_embed()
        else:
            embed = self._get_race_embed()
        await self.send_or_edit_message(embed=embed, view=self._view)

    async def send_or_edit_message(self, content=MISSING, *, embed=MISSING,
                                   view=MISSING):
        if self.message is None:
            if content == MISSING:
                content = None
            if embed == MISSING:
                embed = None
            if view == MISSING:
                view = None
            self.settings['message'] = await self.channel.send(content=content,
                                                               embed=embed,
                                                               view=view)
            await self.save()
        else:
            if type(self.message) == discord.PartialMessage:
                self.settings['message'] = await self.message.fetch()
            try:
                if self.message.content == content:
                    content = MISSING
                if self.message.embeds == [embed]:
                    embed = MISSING
                if view == MISSING and self._view:
                    view = self._view
                if content == MISSING and embed == MISSING and view == MISSING:
                    return
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
        if not self.can_run:
            self._can_run_event.clear()
