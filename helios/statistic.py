#  MIT License
#
#  Copyright (c) 2025 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
import datetime
from typing import Optional, Generator

import discord

from .database import StatisticModel, StatisticHistoryModel


class Stat:
    def __init__(self, name: str, display_name: str = None, description: str = None):
        self.name = name

        self.display_name = display_name
        self.description = description

        self._guild: Optional[int] = None
        self._member: Optional[int] = None

    def setup(self, guild: discord.Guild, member: discord.Member):
        self._guild = guild.id
        self._member = member.id

    async def model(self):
        return await StatisticModel.get(self._guild, self._member, self.name)

    async def value(self):
        return await StatisticModel.get_value(self._guild, self._member, self.name)

    async def increment(self, amount: int = 1):
        await StatisticModel.increment(self._guild, self._member, self.name, amount)

    async def set_value(self, value: int):
        await StatisticModel.set_value(self._guild, self._member, self.name, value)

    async def record_history(self):
        await StatisticHistoryModel.record(await self.model())

    async def get_change_since(self, since: datetime.datetime):
        return await StatisticHistoryModel.get_change_since(await self.model(), since)


class Statistics:
    def __init__(self, guild: discord.Guild, member: discord.Member):
        self.guild = guild
        self.member = member

        self._guild_id = guild.id
        self._member_id = member.id

        self._load_stats()

    def _load_stats(self):
        for stat in self.all_stats():
            new_stat = Stat(stat.name, stat.display_name, stat.description)
            new_stat.setup(self.guild, self.member)
            setattr(self, stat.name, new_stat)

    def all_stats(self) -> Generator['Stat', None, None]:
        for key in dir(self):
            if key.startswith('__'):
                continue
            value = getattr(self, key)
            if isinstance(value, Stat):
                yield value