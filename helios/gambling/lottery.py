import asyncio
import math
import random
from enum import Enum
from datetime import time, datetime, timedelta
from typing import TYPE_CHECKING

import discord

from .image import LotteryImage

if TYPE_CHECKING:
    from ..member import HeliosMember
    from .manager import GamblingManager


__all__ = ('Lottery',)

Ticket = tuple['HeliosMember', list[int]]


class LotteryStatus(Enum):
    scheduled = 0
    running = 1
    finished = 2


class Lottery:
    def __init__(self, manager: 'GamblingManager', pool: int, freq: int, numbers: int, range: int, next_game: datetime,
                 channel: discord.TextChannel, cont: bool, db_entry):
        self.manager = manager
        self.pool = pool
        self.frequency = freq
        self.numbers = numbers
        self.range = range
        self.next_game = next_game
        self.channel: discord.TextChannel = channel
        self.cont = cont
        self.db_entry = db_entry

        self.tickets: list[Ticket] = []

        self.offset_percentage = 0.93

    @classmethod
    async def new(cls, pool: int, freq: int, t: time):
        ...

    async def run(self):
        message = await self.channel.send('Starting Soon')
        image = LotteryImage([], self.numbers)

        then = self.next_game
        while datetime.now() < then:
            remaining = str(then - datetime.now())
            await message.edit(attachments=[image.get_countdown_file(remaining)])
            await asyncio.sleep(1)

        chosen_numbers = self.random_ticket()
        for i in range(self.numbers):
            number = chosen_numbers[i]
            image.numbers.append(number)
            file = image.get_image_file()
            await message.edit(attachments=[file])
            await asyncio.sleep(5)

    async def schedule_next(self):
        ...

    async def calculate_winners(self, winning_numbers: tuple[int]):
        matching = {}
        for ticket in self.tickets:
            member, numbers = ticket
            count = 0
            for n in numbers:
                if n in winning_numbers:
                    count += 1
            if count in matching:
                matching[count].append(ticket)
            else:
                matching[count] = [ticket]
        return matching

    async def payout(self, winners: dict[int, list[Ticket]]):
        payouts: dict['HeliosMember', list] = {}
        win_strs: dict['HeliosMember', str] = {}
        jackpot_winners = []

        for k, v in winners.items():
            if k == self.numbers:
                payout = self.pool
            else:
                payout = self.winnings(k)
            payout //= len(v)
            for ticket in v:
                member, numbers = ticket
                win_str = f'You won {payout:,} {self.manager.server.points_name.capitalize()} with {numbers}\n'
                if k == self.numbers:
                    jackpot_winners.append(member)
                if member in payouts:
                    payouts[member][0] += payout
                    payouts[member][1].append(numbers)
                    win_strs[member] += win_str
                else:
                    payouts[member] = [payout, [numbers]]
                    win_strs[member] = win_str

        for member, payout in payouts.items():
            embed = discord.Embed(
                title='Lottery Winnings',
                description=win_strs[member],
                colour=discord.Colour.green()
            )
            await member.add_points(payout[0], 'Helios: Lottery', 'Lottery Winnings')
            await member.member.send(embed=embed)

        if jackpot_winners:
            embed = discord.Embed(
                title='Jackpot Winner',
                description=f'{", ".join([m.member.display_name for m in jackpot_winners])} won the Jackpot!',
                colour=discord.Colour.gold()
            )
            await self.channel.send(embed=embed)

    def total_combinations(self):
        return math.comb(self.range, self.numbers)

    def jackpot_chance(self):
        return 1 / self.total_combinations()

    def winnings(self, k: int):
        base = self.pool * self.jackpot_chance()
        base /= self.chance_to_get(k)
        return int(base)

    def ways_to_get(self, k: int):
        n = self.range
        r = self.numbers
        x = (math.factorial(r)
             /
             (math.factorial(k) * math.factorial(r-k)))
        y = (math.factorial(n-r)
             /
             (math.factorial((n-r)-(r-k)) * math.factorial(r-k)))
        return x * y

    def chance_to_get(self, k: int):
        return self.ways_to_get(k) / self.total_combinations()

    def random_ticket(self):
        return tuple(random.sample(range(self.range-1), self.numbers))

    def test_odds(self):
        drawn = self.random_ticket()
        smaller_wins = {1: 0, 2: 0, 3: 0, 4: 0}
        diff = 0
        found = 0
        i = 1
        while found == 0:
            ticket = self.random_ticket()
            diff += 100
            matching = 0
            for n in ticket:
                if n in drawn:
                    matching += 1
            if matching == len(drawn):
                found = i
                diff -= self.pool
            elif matching in smaller_wins:
                smaller_wins[matching] += 1
                if matching > 1:
                    diff -= self.winnings(matching) * self.offset_percentage
            i += 1
        print(found)
        print(smaller_wins)
        print(diff)
