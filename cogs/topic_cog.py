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
from discord import app_commands
from discord.ext import commands

from helios import TopicChannel

if TYPE_CHECKING:
    from helios import HeliosBot


class TopicCog(commands.GroupCog, name='topic'):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='new', description='Create a new topic')
    @app_commands.describe(name='The name of the topic. Auto fill shows existing topics.')
    async def topic_create(
            self,
            interaction: discord.Interaction,
            name: str,
    ):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        member = server.members.get(interaction.user.id)
        result, result_message = await server.channels.create_topic(name, member)
        if result:
            await interaction.response.send_message(result_message, ephemeral=True)
            return

        topic = server.channels.get_topic_by_name(name)
        if topic is None:
            await interaction.response.send_message(result_message, ephemeral=True)
            return
        if not topic.active:
            await topic.restore(member, False)
            await topic.save()
            await interaction.response.send_message(f'Channel Restored: {topic.channel.mention}', ephemeral=True)
        else:
            await interaction.response.send_message(f'Channel Exists: {topic.channel.mention}', ephemeral=True)

    @topic_create.autocomplete(name='name')
    async def _topic_create_autocomplete(self, interaction: discord.Interaction, current: str):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        topics = server.channels.topic_channels.values()
        names = [topic.channel.name.replace('🛑', '') for topic in topics[:25]]
        names = [name for name in names if name.startswith(current)]
        return [app_commands.Choice(name=name, value=name) for name in names]

    @app_commands.command(name='add', description='Add an existing channel as a topic')
    @commands.has_permissions(manage_channels=True)
    async def topic_add(
            self,
            interaction: discord.Interaction,
            channel: discord.TextChannel
    ):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        member = server.members.get(interaction.user.id)
        result, result_message = await server.channels.add_topic(channel, member)
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
                if message.author.id == channel.solo_author_id and not channel.channel.permissions_for(message.author).manage_channels:
                    if channel.last_solo_message is None:
                        m = await message.reply('Hey, I see you are the only one to post in this topic in the last week. '
                                                'I will not be cancelling this archive. '
                                                'I will restore it post-archive if anyone messages afterwards.')
                        channel.last_solo_message = m.created_at
                    return
                channel.authors.append(message.author.id)
                await channel.restore(server.members.get(message.author.id))
                await channel.save()


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(TopicCog(bot))
