import random

import discord

from .horse import Horse


class RaceHorse:
    def __init__(self, horse: Horse, jockey=None):
        self.name = horse.name
        self.horse = horse
        self.jockey = jockey
        self.speed = 0
        self.progress = 0
        self.stamina = horse.stamina

    @property
    def max_speed(self) -> float:
        min_max_speed = self.horse.speed * 0.5
        diff = min_max_speed * self.stamina_percentage
        return round(min_max_speed + diff, 2)

    @property
    def speed_increase(self) -> float:
        return round(self.horse.acceleration / 10, 1)

    @property
    def speed_percentage(self) -> float:
        return round(self.speed / self.max_speed, 4)

    @property
    def stamina_percentage(self) -> float:
        return round(self.stamina / self.horse.stamina, 4)

    def get_random_increase(self, variation: float):
        return random.uniform(self.speed_increase * (1 - variation), self.speed_increase)

    def tick_speed(self):
        variation = 0.05
        if self.speed > self.max_speed:
            self.speed = self.max_speed

        if self.speed_percentage < 0.5:
            # Best increase
            self.speed += self.speed_increase
        elif self.speed_percentage < 1:
            # Varied increase
            increase = round(self.get_random_increase(variation), 2)
            self.speed += increase
        else:
            # Potential decrease
            chance_to_decrease = 1 - self.stamina_percentage
            amt_to_decrease = variation * self.speed
            if random.random() <= chance_to_decrease:
                self.speed -= amt_to_decrease

        if self.speed > self.max_speed:
            self.speed = self.max_speed
        return self.speed

    def tick_stamina(self):
        length = 100
        decrease_coefficient = 10 / (length / 10)  # stamina / (track_length / speed)  ---- No this does not make sense.
        decrease_amt = decrease_coefficient * (self.speed / 10)
        self.stamina -= decrease_amt
        if self.stamina < 0:
            self.stamina = 0

    def tick(self) -> float:
        self.progress += self.tick_speed()
        self.tick_stamina()
        return self.speed


class Race:
    def __init__(self, channel: discord.TextChannel):
        self._id = 0
        self.channel = channel
        self.horses: list[RaceHorse] = []
        self.finished: list[RaceHorse] = []
        self.length = 100
        self.phase = 0

    def tick(self):
        for h in self.horses:
            if h.progress < self.length:
                h.tick()
            elif h not in self.finished:
                self.finished.append(h)
        if len(self.finished) >= len(self.horses) - 1:
            self.phase += 1
            if len(self.finished) == len(self.horses) - 1:
                for h in self.horses:
                    if h.progress < self.length:
                        self.finished.append(h)
                        break

    def get_progress_string(self):
        total_size = 10
        filled_char = '▰'
        empty_char = '▱'
        progress_string = ''

        for h in self.horses:
            p = ''
            percent = (h.progress / self.length) * 100
            if percent > 100:
                percent = 100
            filled = int(percent // total_size)
            empty = int(total_size - filled)
            for _ in range(filled):
                p += filled_char
            for _ in range(empty):
                p += empty_char
            progress_string += f'{p} {percent:6.2f}% - {h.name} - {h.stamina_percentage:5.2f} - {h.speed:5.2f} - {h.max_speed:5.2f}\n'
        return progress_string
