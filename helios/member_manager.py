import asyncio
from typing import TYPE_CHECKING
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

    def get(self, member_id: int):
        return self.members.get(member_id)

    async def setup(self, member_data: list[dict] = None):
        if member_data is None:
            member_data = await self.bot.helios_http.get_member(params={'server': self.server.id})
        tasks = []
        member_data_dict = {}
        for data in member_data:
            member_data_dict[data.get('member_id')] = data

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

