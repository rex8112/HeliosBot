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

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from helios import YesNoView

if TYPE_CHECKING:
    from helios import HeliosBot


class EventsCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        server = self.bot.servers.get(member.guild.id)
        helios_member = await server.members.fetch(member.id)
        if not helios_member:
            await server.members.add_member(member)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        server = self.bot.servers.get(guild.id)
        if not server:
            self.bot.servers.add_server(guild)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if message.guild and message.guild.me in message.mentions and message.author.voice:
            if not message.author.voice.channel:
                return
            channel = message.author.voice.channel
            mention_string = ''
            allowed = []
            for m in channel.members:
                mention_string += f'{m.mention} '
                if m != message.author:
                    allowed.append(m)
            view = YesNoView(message.author)
            mess = await message.channel.send(
                f'Would you like to ping everyone in {channel.mention}?',
                view=view,
                delete_after=5
            )
            await view.wait()
            if view.value:
                await message.channel.send(mention_string)
            else:
                try:
                    await mess.delete()
                except discord.NotFound:
                    ...

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState
                                    ):
        server = self.bot.servers.get(member.guild.id)
        helios_member = server.members.get(member.id)
        role = server.voice_controller_role
        if after.channel is None:
            return
        if before.channel is not None:
            return

        await server.do_on_voice(helios_member)

        inactive_channels = server.channels.dynamic_voice.get_inactive()
        for channel in inactive_channels:
            if after.channel.id == channel.channel.id:
                await member.edit(voice_channel=None)
                return

        if role is None:
            return
        if role in member.roles:
            fix = True
            for controller in server.voice_controllers:
                if member in controller.members:
                    fix = False
            if fix:
                await member.edit(mute=False, deafen=False)
                await member.remove_roles(role)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(EventsCog(bot))
