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

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from helios import VoiceTemplate

if TYPE_CHECKING:
    from helios import HeliosBot


logger = logging.getLogger('Helios.PrivateVoiceCog')


class PrivateVoiceCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.clear_context = app_commands.ContextMenu(
            name="Clear from Voice",
            callback=self.clear
        )

        # self.bot.tree.add_command(self.allow_context)
        # self.bot.tree.add_command(self.deny_context)
        self.bot.tree.add_command(self.clear_context)

    async def cog_unload(self) -> None:
        # self.bot.tree.remove_command(self.allow_context.name, type=self.allow_context.type)
        # self.bot.tree.remove_command(self.deny_context.name, type=self.deny_context.type)
        self.bot.tree.remove_command(self.clear_context.name, type=self.clear_context.type)

    async def clear(self, interaction: discord.Interaction,
                    member: discord.Member):
        server = self.bot.servers.get(interaction.guild_id)
        if server:
            private_voices = server.channels.dynamic_voice.get_private()
            private_channel = None
            for channel in private_voices:
                if interaction.user in channel.channel.members and channel.owner == interaction.user:
                    private_channel = channel
                    break
            await interaction.response.defer(ephemeral=True)
            if private_channel:
                channel = private_channel
                template = channel.template
                template.clear(member)
                await channel.apply_template(template)
                await interaction.followup.send(f'{member.mention} Cleared '
                                                f'from {channel.channel.mention}'
                                                '.')
            else:
                await interaction.followup.send(f'You do not currently have a '
                                                f'channel active. Make sure you are currently in the voice channel.')
        else:
            await interaction.response.send_message(
                'Critical Failure, tell `rex8112#1200` that server '
                'initialization failed.'
            )


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(PrivateVoiceCog(bot))
