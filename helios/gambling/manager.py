from typing import TYPE_CHECKING, Union

from discord import TextChannel

from .blackjack import Blackjack

if TYPE_CHECKING:
    from ..server import Server


Games = Union[Blackjack]


class GamblingManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.games: list[Games] = []

    def add_game(self, game: Games):
        self.games.append(game)

    def rem_game(self, game: Games):
        try:
            self.games.remove(game)
        except ValueError:
            ...

    async def run_blackjack(self, channel: TextChannel):
        bj = Blackjack(self, channel)
        self.add_game(bj)
        await bj.run()
        self.rem_game(bj)
