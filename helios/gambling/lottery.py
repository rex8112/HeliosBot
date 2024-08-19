from datetime import time, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import GamblingManager


__all__ = ('Lottery', 'NumbersGame', 'Raffle')


class Lottery:
    def __init__(self, pool: int, freq: int, next_game: datetime, db_entry):
        self.pool = pool
        self.frequency = freq
        self.next_game = next_game
        self.db_entry = db_entry

    @classmethod
    async def new(cls, pool: int, freq: int, t: time):
        ...

    async def run(self):
        ...

    async def schedule_next(self):
        ...


class NumbersGame(Lottery):
    ...


class Raffle(Lottery):
    ...
