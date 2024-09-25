#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
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
from typing import TYPE_CHECKING

import discord


if TYPE_CHECKING:
    from .dynamic_voice import DynamicVoiceChannel
    from .member import HeliosMember


class PUGChannel:
    def __init__(self, voice: 'DynamicVoiceChannel'):
        self.voice = voice

        self.server_members: list['HeliosMember'] = []
        self.temporary_members: list['HeliosMember'] = []
        self.role: discord.Role = None
        self.invite: discord.Invite = None

    def get_members(self):
        return self.server_members + self.temporary_members

    async def create_role(self):
        if self.role:
            return
        self.role = await self.voice.channel.guild.create_role(name='PUG Role', mentionable=True)

    async def create_invite(self):
        if self.invite:
            return
        self.invite = await self.voice.channel.create_invite(max_age=24 * 60 * 60, max_uses=0, reason='PUG Invite')

    async def add_member(self, member: 'HeliosMember'):
        if member in self.server_members:
            return
        await member.member.add_roles(self.role)
        self.server_members.append(member)

    async def remove_member(self, member: 'HeliosMember'):
        if member not in self.server_members:
            return
        await member.member.remove_roles(self.role)
        self.server_members.remove(member)

    async def add_temporary_member(self, member: 'HeliosMember'):
        if member in self.temporary_members:
            return
        await member.member.add_roles(self.role)
        self.temporary_members.append(member)

    async def remove_temporary_member(self, member: 'HeliosMember'):
        if member not in self.temporary_members:
            return
        await member.member.remove_roles(self.role)
        self.temporary_members.remove(member)

    async def ensure_members_have_role(self):
        for member in self.server_members + self.temporary_members:
            await member.member.add_roles(self.role)

    async def end_pug(self):
        await self.role.delete()
        await self.invite.delete()
        asyncio.create_task(self.voice.make_inactive())
