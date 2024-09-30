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
from .database import PugModel

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

        self.db_entry = None

    @classmethod
    async def create(cls, server: 'Server', name: str, server_members: list['HeliosMember'],
                     temporary_members: list['HeliosMember'], voice: 'DynamicVoiceChannel' = None):
        voice = await server.channels.dynamic_voice.get_inactive_channel() if not voice else voice
        with voice:
            role = await cls.create_role(voice, name)
            invite = await cls.create_invite(voice)
            self = cls(voice, server_members, temporary_members, role, invite)
            await voice.make_controlled(view_cls(self))
            voice.custom_name = name
            self.db_entry = await PugModel.create(server_id=server.guild.id, channel_id=voice.channel.id,
                                                  invite=invite.id, role=role.id)
            await self.save()
            return self

    @staticmethod
    async def create_role(voice: 'DynamicVoiceChannel', name: str):
        return await voice.channel.guild.create_role(name=f'PUG {name}', mentionable=True)

    @staticmethod
    async def create_invite(voice: 'DynamicVoiceChannel'):
        return await voice.channel.create_invite(max_age=24 * 60 * 60, max_uses=0, reason='PUG Invite')

    async def save(self):
        await self.db_entry.async_update(**self.to_dict())

    def to_dict(self):
        return {
            'server_members': [m.member.id for m in self.server_members],
            'temporary_members': [m.member.id for m in self.temporary_members],
            'role': self.role.id,
            'invite': self.invite.id
        }

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
        self.server_members.append(member)
        if self.role not in member.member.roles:
            await member.member.add_roles(self.role)
        await self.save()

    async def remove_member(self, member: 'HeliosMember'):
        if member not in self.server_members:
            return
        self.server_members.remove(member)
        if self.role in member.member.roles:
            await member.member.remove_roles(self.role)
        await self.save()

    async def add_temporary_member(self, member: 'HeliosMember'):
        if member in self.temporary_members:
            return
        self.temporary_members.append(member)
        if self.role not in member.member.roles:
            await member.member.add_roles(self.role)
        await self.save()

    async def remove_temporary_member(self, member: 'HeliosMember', *, kick=False):
        if member not in self.temporary_members:
            return
        self.temporary_members.remove(member)
        if kick:
            await member.member.kick(reason='PUG Ended')
        else:
            await member.member.remove_roles(self.role)
        await self.save()

    async def ensure_members_have_role(self):
        for member in self.server_members + self.temporary_members:
            await member.member.add_roles(self.role)

    async def ensure_role_members_in_pug(self):
        for member in self.role.members:
            member = self.voice.server.members.get(member.id)
            if member not in self.server_members + self.temporary_members:
                if member.verified:
                    await self.add_member(member)
                else:
                    await self.add_temporary_member(member)
                await self.voice.update_control_message(force=True)

    async def end_pug(self):
        for member in self.temporary_members:
            if not member.verified:
                await self.remove_temporary_member(member, kick=True)
        await self.role.delete()
        await self.invite.delete()
        if self.voice.channel.members:
            asyncio.create_task(self.voice.make_active(list(self.voice.manager.groups.values())[0]))
        else:
            asyncio.create_task(self.voice.make_inactive())


class PUGManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.pugs: list[PUGChannel] = []
        self.invites: dict[discord.Invite, int] = {}

    async def create_pug(self, name: str, leader: 'HeliosMember', voice: 'DynamicVoiceChannel' = None):
        pug = await PUGChannel.create(self.server, name, [leader], [], voice)
        self.pugs.append(pug)
        self.invites[pug.invite] = pug.invite.uses
        return pug

    async def load_pugs(self):
        pugs_data = await PugModel.get_all(self.server.db_entry)
        for pug_data in pugs_data:
            save = False
            voice = self.server.channels.dynamic_voice.get(pug_data.channel_id)
            if not voice:
                continue
            server_members = [self.server.members.get(m) for m in pug_data.server_members]
            temporary_members = [self.server.members.get(m) for m in pug_data.temporary_members]
            role = self.server.guild.get_role(pug_data.role)
            if not role:
                role = await PUGChannel.create_role(voice, voice.custom_name)
                save = True
            invite = discord.utils.find(lambda x: x.id == pug_data.invite, await self.server.guild.invites())
            if not invite:
                invite = await PUGChannel.create_invite(voice)
                save = True
            pug = PUGChannel(voice, server_members, temporary_members, role, invite)
            self.pugs.append(pug)
            self.invites[invite] = invite.uses
            await pug.ensure_members_have_role()
            if save:
                await pug.save()

    async def on_member_join(self, member: discord.Member):
        for invite in await self.server.guild.invites():
            if invite not in self.invites:
                continue
            if invite.uses > self.invites.get(invite, 0):
                self.invites[invite] = invite.uses
                for pug in self.pugs:
                    if invite == pug.invite:
                        await pug.add_temporary_member(self.server.members.get(member))
                        await pug.voice.update_control_message(force=True)
                        break

    async def manage_pugs(self):
        for pug in self.pugs:
            if len(pug.voice.channel.members) == 0:
                await pug.end_pug()
                self.pugs.remove(pug)
                del self.invites[pug.invite]
            else:
                await pug.ensure_members_have_role()
                await pug.ensure_role_members_in_pug()


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
            view = PUGKeepView(self.pug)
            await interaction.response.send_message('Select members to keep in server', view=view)
            await view.wait()
            if view.selected:
                for member in view.selected:
                    await self.pug.add_member(member)
            await self.pug.end_pug()
            await interaction.response.send_message('PUG Ended', ephemeral=True)


    return PUGView


class PUGKeepView(discord.ui.View):
    """Displays at the end of a PUG group to allow the leader to keep temporary members in the server"""
    def __init__(self, pug: PUGChannel):
        super().__init__(timeout=300)
        self.pug = pug
        self.selected: list['HeliosMember'] = []

        self.keep_members.options = [discord.SelectOption(label=m.member.display_name, value=str(i))
                                     for i, m in enumerate(self.pug.temporary_members)]
        self.keep_members.max_values = len(self.pug.temporary_members)

    @discord.ui.select(placeholder='Select Members to Keep in Server', min_values=1)
    async def keep_members(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected = [self.pug.temporary_members[int(v)] for v in select.values]
        await interaction.response.send_message(f'{len(self.selected)} members selected', ephemeral=True)

    @discord.ui.button(label='Continue', style=discord.ButtonStyle.green)
    async def continue_(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.stop()
