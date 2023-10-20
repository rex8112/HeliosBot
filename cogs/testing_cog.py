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
import concurrent.futures
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from helios import HeliosBot

TESTING_GUILD = discord.Object(id=466060673651310593)


class TestingCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def guild_sync(self, ctx: commands.Context):
        self.bot.tree.copy_global_to(guild=TESTING_GUILD)
        await self.bot.tree.sync(guild=TESTING_GUILD)
        await ctx.send(f'Commands Synced to {TESTING_GUILD.id}')

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync()
        await ctx.send('Commands Synced')

    @app_commands.command(name='ping')
    async def ping_command(self, interaction: discord.Interaction):
        """ /ping """
        await interaction.response.send_message('Pong!')

    @app_commands.command(name='play')
    async def play_command(self, interaction: discord.Interaction, song: str):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        if interaction.user.voice is None:
            await interaction.response.send_message(content='Must be in a VC', ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        if not server.music_player.is_connected():
            await server.music_player.join_channel(interaction.user.voice.channel)
        regex = r'https:\/\/(?:www\.)?youtu(?:be\.com|\.be)\/(?:watch\?v=)?([^"&?\/\s]{11})'
        matches = re.match(regex, song, re.RegexFlag.I)
        if matches:
            await server.music_player.add_song_url(song, member)
            await interaction.followup.send(content='Song Queued')
        else:
            await interaction.followup.send(content='Invalid URL Given')


async def setup(bot: 'HeliosBot') -> None:
    await bot.add_cog(TestingCog(bot))
