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
import asyncio
from datetime import time, datetime, timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

from helios.database import StatisticModel

if TYPE_CHECKING:
    from helios import HeliosBot


class StatisticsCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.update_statistics.start()
        self.daily_statistics.start()

    def cog_unload(self):
        self.update_statistics.stop()
        self.daily_statistics.stop()

    @app_commands.command(name='stats', description='Look at your current stats')
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        embed = discord.Embed(
            title=f'Statistics for {member.member.display_name}',
            color=discord.Color.blue()
        )
        embed.set_footer(text='This is just a placeholder')
        description = 'Total statistics:'
        for stat in member.statistics.all_stats():
            value = await stat.value()
            description += f'\n**{stat.display_name}**: {value}'
        embed.description = description
        await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        server = self.bot.servers.get(message.guild.id)
        member = server.members.get(message.author.id)
        if not member:
            return
        if not server.cooldowns.on_cooldown('message_stat', message.author.id):
            server.cooldowns.set_duration('message_stat', message.author.id, 15)
            await member.statistics.limited_messages.increment()

        await member.statistics.messages.increment()

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=datetime.now().astimezone().tzinfo))
    async def daily_statistics(self):
        await StatisticModel.record_all()

    @tasks.loop(minutes=1)
    async def update_statistics(self):
        updates = []
        for server in self.bot.servers.servers.values():
            for channel in server.guild.voice_channels:
                if channel.members:
                    for member in channel.members:
                        if member.bot:
                            continue
                        helios_member = server.members.get(member.id)
                        if helios_member:
                            if channel == channel.guild.afk_channel:
                                updates.append(helios_member.statistics.afk_time.increment())
                            else:
                                updates.append(helios_member.statistics.voice_time.increment())
                                if len(list(filter(lambda x: not x.bot, channel.members))) == 1:
                                    updates.append(helios_member.statistics.alone_time.increment())
                                if helios_member.get_game_activity():
                                    updates.append(helios_member.statistics.game_time.increment())
        if updates:
            await asyncio.gather(*updates)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(StatisticsCog(bot))
