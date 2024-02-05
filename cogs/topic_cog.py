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

from helios import TopicCreation, TopicChannel

if TYPE_CHECKING:
    from helios import HeliosBot, Server


class TopicCog(commands.GroupCog, name='topic'):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='new', description='Create a new topic')
    async def topic_create(
            self,
            interaction: discord.Interaction,
            name: str,
    ):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        member = server.members.get(interaction.user.id)
        result, result_message = await server.channels.create_topic(name, member)
        await interaction.response.send_message(result_message, ephemeral=True)

    @app_commands.command(name='pin', description='Pin a topic')
    @commands.has_permissions(manage_channels=True)
    async def topic_pin(
            self,
            interaction: discord.Interaction,
            channel: discord.TextChannel
    ):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        member = server.members.get(interaction.user.id)
        topic = server.channels.get(channel.id)
        if isinstance(topic, TopicChannel):
            await topic.pin(member)
            await topic.save()
            pinned = topic.pinned
            await interaction.response.send_message(f'Topic is now {"pinned" if pinned else "unpinned"}',
                                                    ephemeral=True)
        else:
            await interaction.response.send_message(f'Channel is not a topic', ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user or message.guild is None:
            return
        server = self.bot.servers.get(guild_id=message.guild.id)
        channel = server.channels.get(message.channel.id)
        if isinstance(channel, TopicChannel):
            if not channel.active:
                await channel.restore(server.members.get(message.author.id))
                await channel.save()


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(TopicCog(bot))
