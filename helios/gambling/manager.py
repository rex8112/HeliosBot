from datetime import timedelta
from typing import TYPE_CHECKING, Union

from discord import TextChannel

from .blackjack import Blackjack
from .lottery import *

if TYPE_CHECKING:
    from ..server import Server
    from ..member import HeliosMember


Games = Union[Blackjack]
HelpCooldown = 24 * 60 * 60


class GamblingManager:
    def __init__(self, server: 'Server'):
        self.server = server

        self.games: list[Games] = []
        self.lotteries: list[Lottery] = []
        self.loss_streak: dict['HeliosMember', int] = {}

    def add_loss(self, member: 'HeliosMember', loss: int):
        if loss < 0:
            self.loss_streak[member] = 0
        elif member not in self.loss_streak:
            self.loss_streak[member] = loss
        else:
            self.loss_streak[member] += loss

    async def needs_help(self, member: 'HeliosMember'):
        if self.server.cooldowns.on_cooldown('gambling.helped', member):
            return False
        if member not in self.loss_streak:
            return False

        if await member.get_activity_points() < 10_000:
            return False
        if self.loss_streak[member] > member.points >= 1_000:
            return True
        return False

    def helped(self, member: 'HeliosMember'):
        self.server.cooldowns.set_duration('gambling.helped', member, HelpCooldown)

    def add_game(self, game: Games):
        self.games.append(game)

    def rem_game(self, game: Games):
        try:
            self.games.remove(game)
        except ValueError:
            ...

    def can_run_blackjack(self, channel: TextChannel):
        if channel in [game.channel for game in self.games if isinstance(game, Blackjack)]:
            return False
        return True

    async def run_blackjack(self, channel: TextChannel):
        bj = Blackjack(self, channel)
        self.add_game(bj)
        await bj.start()
        self.rem_game(bj)
