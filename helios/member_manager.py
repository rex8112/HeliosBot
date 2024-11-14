#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
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

import asyncio
from typing import TYPE_CHECKING, Union, Optional

import discord
import peewee

from .database import MemberModel, objects
from .member import HeliosMember

if TYPE_CHECKING:
    from .server import Server


class MemberManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.members: dict[int, HeliosMember] = {}

    @property
    def bot(self):
        return self.server.bot

    @property
    def guild(self):
        return self.server.guild

    def get(self, member_id: Union[int, discord.Member]) -> Optional[HeliosMember]:
        if isinstance(member_id, discord.Member):
            member_id = member_id.id
        return self.members.get(member_id)

    async def fetch(self, member_id: int, *, force=False):
        member = self.get(member_id)
        if member and not force:
            return member
        try:
            mem_data = await objects.get(MemberModel, member_id=member_id, server_id=self.guild.id)
        except peewee.DoesNotExist:
            mem_data = None
        mem = self.guild.get_member(member_id)
        if mem_data and mem:
            member = HeliosMember(self, mem, data=mem_data)
            self.members[member_id] = member
            return member
        return None

    async def add_member(self, mem: discord.Member):
        h = HeliosMember(self, mem)
        self.members[mem.id] = h
        await h.save()
        return h

    async def manage_members(self):
        await self.bot.wait_until_ready()
        await self.check_voices()
        await self.save_all()

    async def check_voices(self):
        tasks = []
        settings = self.server.settings
        for m in self.members.values():
            tasks.append(m.check_voice(settings.points_per_minute.value, settings.partial.value))
        if tasks:
            await asyncio.gather(*tasks)

    async def save_all(self):
        saves = []
        for m in self.members.values():
            saves.append(m.save())
        if len(saves) > 0:
            await asyncio.gather(*saves)

    async def setup(self, member_data: list[MemberModel] = None):
        if member_data is None:
            member_data = MemberModel.select().where(MemberModel.server == self.server.id)
        tasks = []
        member_data_dict = {}
        for data in member_data:
            member_data_dict[data.member_id] = data

        for member in self.guild.members:
            data = member_data_dict.get(member.id)
            if data:
                m = HeliosMember(self, member, data=data)
            else:
                m = HeliosMember(self, member)
                tasks.append(m.save())
            tasks.append(m.load_inventory())
            self.members[m.member.id] = m
        if len(tasks) > 0:
            await asyncio.gather(*tasks)
        #  self.bot.loop.create_task(self.manage_members())

