import datetime
import random
from typing import Optional, TYPE_CHECKING

import discord

from .horse import Horse
from ..abc import HasSettings
from ..types.horses import MaxRaceHorses
from ..types.settings import EventRaceSettings

if TYPE_CHECKING:
    from ..stadium import Stadium


class Record:
    def __init__(self):
        self.id = 0
        self.horse_id = 0
        self.race_type = 'None'
        self.earnings = 0
        self.placing = 0

    @classmethod
    def new(cls, horse: 'RaceHorse', event_race: 'EventRace', earnings: float):
        if not event_race.finished:
            raise ValueError('event_race must be finished')
        record = cls()
        record.id = 0
        record.horse_id = horse.horse.id
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
            'type': self.race_type,
            'earnings': self.earnings,
            'placing': self.placing
        }

    def _deserialize(self, data: dict):
        self.id = data['id']
        self.horse_id = data['horse']
        self.race_type = data['type']
        self.earnings = data['earnings']
        self.placing = data['placing']


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

    @property
    def max_speed(self) -> float:
        max_speed = RaceHorse.BASE_SPEED + (self.horse.speed * 0.1) * RaceHorse.SPEED_LIMITER_MULTIPLIER
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
        return random.uniform(self.speed_increase * (1 - variation), self.speed_increase)

    def tick_speed(self):
        acceleration_variation = 0.2
        acceleration_multiplier = 1
        target = 0.8
        min_speed = 0.5
        max_speed = 1
        if self.speed > self.max_speed:
            self.speed = self.max_speed

        if self.speed_percentage < min_speed:
            # Best increase
            self.speed += self.speed_increase
        elif not self.achieved_target:
            # Varied increase
            increase = round(self.get_random_increase(acceleration_variation), 4)
            self.speed += increase
            if self.speed_percentage >= target:
                self.achieved_target = True
        else:
            # Potential decrease
            if self.speed_percentage < target:
                chance_to_decrease = 0.33  # Chance to decrease when lower than target speed
            elif self.speed_percentage > target:
                chance_to_decrease = 0.66  # Chance to decrease when faster than target speed
            else:
                chance_to_decrease = 0.5  # Chance to decrease when matching target speed - Very unlikely scenario
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


class Race:
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
            elif h not in self.finished_horses:
                h.tick_finished = self.tick_number
                self.finished_horses.append(h)

        self.finished_horses.sort(key=lambda x: (x.tick_finished, -x.progress))

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
        return sorted(self.horses, key=lambda rh: rh.progress, reverse=True)

    def get_progress_string(self):
        total_size = 50
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
            progress_string += f'{p} {position_sorted_list.index(h) + 1:2} {percent:7.3f}% - {h.name}\n'
        return progress_string


class EventRace(HasSettings):
    _default_settings: EventRaceSettings = {
        'channel': None,
        'message': None,
        'purse': 75000,
        'stake': 4000,
        'max_horses': 6,
        'type': 'maiden',
        'race_time': datetime.datetime.now().astimezone(),
        'betting_time': 15 * 60
    }

    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self._id = 0
        self.name = ''
        self.race: Optional[Race] = None
        self.horses: list[Horse] = []
        self.bets = []

        self.settings: EventRaceSettings = EventRace._default_settings.copy()

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
    def time_until_race(self) -> datetime.timedelta:
        now = datetime.datetime.now().astimezone()
        return self.settings['race_time'] - now

    @property
    def time_until_betting(self) -> datetime.timedelta:
        return self.time_until_race - datetime.timedelta(self.settings['betting_time'])

    def _get_race_embed(self) -> discord.Embed:
        if not self.race:
            desc_string = f'The {self.name} is about to commence!'
        elif self.finished:
            desc_string = f'{self.race.finished_horses[0]} has won the race!'
        else:
            desc_string = self.race.get_progress_string()

        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title=self.name,
            description=desc_string
        )
        embed.add_field(
            name='Race Information',
            value=(
                f'Purse: {self.purse}\n'
                f'Stake: {self.stake}\n'
                f'Type: {self.settings["type"].capitalize()}\n'
                f'Horses: {self.max_horses}'
            )
        )
        horse_string = ''
        for h in self.horses:
            owner = h.settings['owner'].member
            if not owner:
                owner = self.stadium.owner
            horse_string += f'{h.name} - {owner.mention}'

        return embed

    def generate_race(self) -> Race:
        race = Race()
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

    def payout_horses(self):
        payout = self.get_payout_amount(self.get_payout_structure())
        for i, h in enumerate(self.race.finished_horses):
            h.horse.pay(payout[i])
