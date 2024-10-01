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
import io
from typing import TYPE_CHECKING

import discord
from PIL import Image
from discord import app_commands
from discord.ext import commands
from websockets import serve

from helios.views.generic_views import DateTimeView

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

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        await self.bot.close()

    @app_commands.command(name='ping')
    async def ping_command(self, interaction: discord.Interaction):
        """ /ping """
        await interaction.response.send_message('Pong!')

    @app_commands.command(name='manage_games')
    async def manage_games(self, interaction: discord.Interaction):
        """ Test the manage games loop """
        await interaction.response.defer(ephemeral=True)
        server = self.bot.servers.get(interaction.guild_id)
        await server.games.manage_games()
        await interaction.followup.send('Done')

    @app_commands.command(name='set_day_playtime')
    async def set_day_playtime(self, interaction: discord.Interaction):
        """ Test the set day playtime loop """
        await interaction.response.defer(ephemeral=True)
        server = self.bot.servers.get(interaction.guild_id)
        await server.games.set_day_playtime()
        await interaction.followup.send('Done')

    # @app_commands.command(name='riverimage')
    async def river_image(self, interaction: discord.Interaction):
        """Post a picture example for the river"""
        img = Image.open('./helios/resources/RiverTemplate.png')
        b = io.BytesIO()
        img.save(b, format='PNG')
        b.seek(0)
        embed = discord.Embed(
            title='Testing'
        )
        embed.set_image(url='attachment://river.png')
        await interaction.response.send_message(embed=embed, file=discord.File(b, 'river.png'))
        b.close()

    # @app_commands.command(name='activity')
    async def activity_command(self, interaction: discord.Interaction):
        """ /activity """
        guild = self.bot.get_guild(interaction.guild_id)
        message = ''
        for channels in guild.voice_channels:
            for member in channels.members:
                activity = ', '.join([' - '.join([type(a).__name__, a.name]) for a in member.activities])
                if activity:
                    message += f'{member.display_name}: {activity}\n'
                else:
                    message += f'{member.display_name}: None\n'
        await interaction.response.send_message(f'```{message}```')

    # @app_commands.command(name='channelpositions')
    async def channel_positions(self, interaction: discord.Interaction):
        """ /channelpositions """
        guild = self.bot.get_guild(interaction.guild_id)
        message = ''
        for channel in guild.channels:
            message += f'{channel.name}: {channel.position}\n'
        await interaction.response.send_message(f'```{message}```', ephemeral=True)


async def setup(bot: 'HeliosBot') -> None:
    await bot.add_cog(TestingCog(bot))
