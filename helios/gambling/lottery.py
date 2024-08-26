import math
import random
from enum import Enum
from datetime import time, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import GamblingManager


__all__ = ('Lottery',)


class LotteryStatus(Enum):
    scheduled = 0
    running = 1
    finished = 2


class Lottery:
    def __init__(self, pool: int, freq: int, numbers: int, range: int, next_game: datetime, db_entry):
        self.pool = pool
        self.frequency = freq
        self.next_game = next_game
        self.db_entry = db_entry

        self.numbers = numbers
        self.range = range

        self.offset_percentage = 0.93

    @classmethod
    async def new(cls, pool: int, freq: int, t: time):
        ...

    async def run(self):
        ...

    async def schedule_next(self):
        ...

    def total_permutations(self):
        return math.perm(self.range, self.numbers)

    def jackpot_chance(self):
        return 1 / self.total_permutations()

    def chance_to_get(self, k: int):
        n = self.range
        r = self.numbers
        x = (math.factorial(r)
             /
             (math.factorial(k) * math.factorial(r-k)))
        y = (math.factorial(n-r)
             /
             (math.factorial((n-r)-(r-k)) * math.factorial(r-k)))
        return x * y / self.total_permutations()

    def random_ticket(self):
        return tuple(random.sample(range(self.range-1), self.numbers))

    def test_odds(self):
        drawn = self.random_ticket()
        found = 0
        i = 1
        while found == 0:
            ticket = self.random_ticket()
            print(ticket)
            if ticket == drawn:
                found = i
            i += 1
        print(found)