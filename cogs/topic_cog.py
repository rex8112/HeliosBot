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

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from helios import TopicCreation

if TYPE_CHECKING:
    from helios import HeliosBot, Server


class TopicCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='topic', description='Create a new topic')
    async def topic_create(
            self,
            interaction: discord.Interaction,
            channel: Optional[discord.TextChannel] = None,
            tier: Optional[int] = 1
    ):
        if channel:
            if channel.permissions_for(interaction.user).manage_channels:
                bot: 'HeliosBot' = interaction.client
                server: 'Server' = bot.servers.get(interaction.guild_id)
                result, result_message = await server.channels.add_topic(channel, interaction.user, tier)
                await interaction.response.send_message(result_message, ephemeral=True)
            else:
                await interaction.response.send_message(
                    'You do not have permission to do this, try without parameters',
                    ephemeral=True
                )
        else:
            await interaction.response.send_modal(TopicCreation())


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(TopicCog(bot))
