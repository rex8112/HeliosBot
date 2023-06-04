import asyncio
from typing import TYPE_CHECKING

import discord
import peewee

from .member import HeliosMember
from .database import MemberModel

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

    def get(self, member_id: int):
        return self.members.get(member_id)

    async def fetch(self, member_id: int, *, force=False):
        member = self.get(member_id)
        if member and not force:
            return member
        try:
            mem_data = await MemberModel.get(id=member_id)
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
        self.check_voices()
        await self.save_all()

    def check_voices(self):
        for m in self.members.values():
            settings = self.server.settings
            m.check_voice(settings.points_per_minute, settings.partial)

    async def save_all(self):
        saves = []
        for m in self.members.values():
            saves.append(m.save())
        if len(saves) > 0:
            await asyncio.wait(saves)

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
            self.members[m.member.id] = m
        if len(tasks) > 0:
            await asyncio.wait(tasks)
        #  self.bot.loop.create_task(self.manage_members())

