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

import datetime
from typing import Optional, TYPE_CHECKING

import discord

from ..modals import VoiceNameChange
from helios.types import HeliosChannel

__all__ = ('VoiceView',)

if TYPE_CHECKING:
    from ..channel import VoiceChannel


class VoiceView(discord.ui.View):
    def __init__(self, voice: 'VoiceChannel'):
        super().__init__(timeout=None)
        self.bot = voice.bot
        self.voice = voice
        if self.voice.get_template().private:
            self.whitelist.disabled = True
        else:
            self.blacklist.disabled = True

    def get_channel(self, guild_id: int,
                    channel_id: int) -> Optional['HeliosChannel']:
        server = self.bot.servers.get(guild_id)
        if server:
            channel = server.channels.get(channel_id)
            return channel
        return None

    @discord.ui.button(label='Change Name', style=discord.ButtonStyle.gray,
                       custom_id='voice:name')
    async def change_name(self, interaction: discord.Interaction,
                          _: discord.ui.Button):
        voice: 'VoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        now = datetime.datetime.now().astimezone()
        if voice.next_name_change() <= now:
            await interaction.response.send_modal(VoiceNameChange(voice))
        else:
            await interaction.response.send_message(
                f'Try again <t:{int(voice.next_name_change().timestamp())}:R>',
                ephemeral=True
            )

    @discord.ui.button(label='Make Private', style=discord.ButtonStyle.green)
    async def whitelist(self, interaction: discord.Interaction,
                        _: discord.ui.Button):
        voice: 'VoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        template = voice.get_template()
        template.private = True
        await interaction.response.defer()
        await voice.update_permissions(template)
        await voice.update_message()
        await template.save()

    @discord.ui.button(label='Make Public', style=discord.ButtonStyle.red)
    async def blacklist(self, interaction: discord.Interaction,
                        _: discord.ui.Button):
        voice: 'VoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        template = voice.get_template()
        template.private = False
        await interaction.response.defer()
        await voice.update_permissions(template)
        await voice.update_message()
        await template.save()

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder='Add to Allowed')
    async def allow_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        voice: 'VoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        member = select.values[0]
        await interaction.response.defer(thinking=True, ephemeral=True)
        await self.voice.allow(member)
        await interaction.followup.send(f'{member.mention} Allowed in '
                                        f'{self.voice.channel.mention}.')

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder='Add to Denied')
    async def deny_user(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        voice: 'VoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        member = select.values[0]
        await interaction.response.defer(thinking=True, ephemeral=True)
        await self.voice.deny(member)
        await interaction.followup.send(f'{member.mention} Denied in '
                                        f'{self.voice.channel.mention}.')
