import random
from typing import Optional

import discord

from .horse import Horse
from ..abc import HasSettings
from ..types.horses import MaxRaceHorses
from ..types.settings import EventRaceSettings


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
        'type': 'maiden'
    }

    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self._id = 0
        self.name = ''
        self.race: Optional[Race] = None
        self.horses: list[Horse] = []
        self.bets = []

        self.settings = EventRace._default_settings.copy()

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
