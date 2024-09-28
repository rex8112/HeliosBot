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

from .colour import Colour

if TYPE_CHECKING:
    from .dynamic_voice import DynamicVoiceChannel
    from .member import HeliosMember
    from .server import Server


class PUGChannel:
    def __init__(self, voice: 'DynamicVoiceChannel', server_members: list['HeliosMember'], temporary_members: list['HeliosMember'],
                 role: discord.Role, invite: discord.Invite):
        self.voice = voice

        self.server_members: list['HeliosMember'] = server_members
        self.temporary_members: list['HeliosMember'] = temporary_members
        self.role: discord.Role = role
        self.invite: discord.Invite = invite

    @classmethod
    async def create(cls, server: 'Server', name: str, server_members: list['HeliosMember'],
                     temporary_members: list['HeliosMember']):
        voice = await server.channels.dynamic_voice.get_inactive_channel()
        with voice:
            role = await cls.create_role(voice)
            invite = await cls.create_invite(voice)
            self = cls(voice, server_members, temporary_members, role, invite)
            await voice.make_controlled(view_cls(self))
            voice.custom_name = name

    @staticmethod
    async def create_role(voice: 'DynamicVoiceChannel'):
        return await voice.channel.guild.create_role(name=f'PUG {voice.custom_name}', mentionable=True)

    @staticmethod
    async def create_invite(voice: 'DynamicVoiceChannel'):
        return await voice.channel.create_invite(max_age=24 * 60 * 60, max_uses=0, reason='PUG Invite')

    def get_members(self):
        return self.server_members + self.temporary_members

    def get_leader(self):
        return self.server_members[0] if self.server_members else None

    def get_overwrites(self) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
        overwrites = {
            self.role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, stream=True, use_voice_activation=True),
            self.voice.server.bot: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, use_voice_activation=True),
            self.voice.server.guild.default_role: discord.PermissionOverwrite(speak=False, stream=False, use_soundboard=False),
            self.get_leader().member: discord.PermissionOverwrite(priority_speaker=True)
        }
        return overwrites


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

    async def remove_temporary_member(self, member: 'HeliosMember', *, kicked=False):
        if member not in self.temporary_members:
            return
        if kicked:
            ...
        else:
            await member.member.remove_roles(self.role)
        self.temporary_members.remove(member)

    async def ensure_members_have_role(self):
        for member in self.server_members + self.temporary_members:
            await member.member.add_roles(self.role)

    async def end_pug(self):
        await self.role.delete()
        await self.invite.delete()
        asyncio.create_task(self.voice.make_inactive())


def view_cls(pug: PUGChannel):
    class PUGView(discord.ui.View):
        def __init__(self, voice: 'DynamicVoiceChannel'):
            super().__init__(timeout=None)
            self.voice = voice
            self.pug = pug

            self.remove_member.options = [discord.SelectOption(label=m.member.display_name, value=str(m.member.id))
                                          for m in self.pug.get_members() if m != self.pug.get_leader()]

        def get_embed(self):
            embed = discord.Embed(
                title=self.voice.custom_name,
                description=self.pug.invite.url,
                colour=Colour.helios()
            )
            embed.add_field(name='Leader', value=self.pug.get_leader().member.mention if self.pug.get_leader() else 'None')
            embed.add_field(name='Members', value='\n'.join([m.member.mention for m in self.pug.get_members()]))
            return embed

        @discord.ui.select(placeholder='Add Member', cls=discord.ui.UserSelect)
        async def add_member(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
            member = self.voice.server.members.get(select.values[0].id)
            await self.pug.add_member(member)
            await interaction.response.send_message(f'{member.mention} added to PUG group', ephemeral=True)
            await self.voice.update_control_message(force=True)

        @discord.ui.select(placeholder='Remove Member')
        async def remove_member(self, interaction: discord.Interaction, select: discord.ui.Select):
            member = self.voice.server.members.get(select.values[0])
            if member in self.pug.server_members:
                await self.pug.remove_member(member)
            elif member in self.pug.temporary_members:
                await self.pug.remove_temporary_member(member)
            else:
                await interaction.response.send_message(f'{member.mention} not in PUG group', ephemeral=True)
                await self.voice.update_control_message(force=True)
                return
            await interaction.response.send_message(f'{member.mention} removed from PUG group', ephemeral=True)
            await self.voice.update_control_message(force=True)

        @discord.ui.button(label='End PUG', style=discord.ButtonStyle.red)
        async def end_pug(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.pug.get_leader().member != interaction.user:
                await interaction.response.send_message('Only the leader can end the PUG group', ephemeral=True)
            await self.pug.end_pug()
            await interaction.response.send_message('PUG Ended', ephemeral=True)


    return PUGView


class PUGKeepView(discord.ui.View):
    """Displays at the end of a PUG group to allow the leader to keep temporary members in the server"""
    def __init__(self, pug: PUGChannel):
        super().__init__(timeout=300)
        self.pug = pug
        self.selected = []

        self.keep_members.options = [discord.SelectOption(label=m.member.display_name, value=str(i))
                                     for i, m in enumerate(self.pug.temporary_members)]
        self.keep_members.max_values = len(self.pug.temporary_members)

    @discord.ui.select(placeholder='Select Members to Keep  in Server', min_values=1)
    async def keep_members(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected = [self.pug.temporary_members[int(v)] for v in select.values]
        await interaction.response.send_message(f'{len(self.selected)} members selected', ephemeral=True)

    @discord.ui.button(label='Continue', style=discord.ButtonStyle.green)
    async def continue_(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.stop()
