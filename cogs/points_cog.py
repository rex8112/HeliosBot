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
import re
from datetime import time, datetime

from discord import app_commands
from discord.ext import commands, tasks

import helios
from helios import ShopView
from helios.shop import *

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember


def get_leaderboard_string(num: int, member: 'HeliosMember', value: int, prefix: str = ''):
    return f'{prefix:2}{num:3}. {member.member.display_name:>32}: {value:10,}\n'


def build_leaderboard(author: 'HeliosMember', members: list['HeliosMember'], key: Callable[['HeliosMember'], int]) -> str:
    s_members = sorted(members, key=lambda x: -key(x))
    leaderboard_string = ''
    user_found = False
    for i, mem in enumerate(s_members[:10], start=1):  # type: int, HeliosMember
        modifier = ''
        if mem == author:
            modifier = '>'
            user_found = True
        leaderboard_string += get_leaderboard_string(i, mem, key(mem), modifier)
    if not user_found:
        index = s_members.index(author)
        leaderboard_string += '...\n'
        for i, mem in enumerate(s_members[index - 1:index + 2], start=index):
            modifier = ''
            if mem == author:
                modifier = '>'
            leaderboard_string += get_leaderboard_string(i, mem, key(mem), modifier)
    return leaderboard_string


class PointsCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.pay_ap.start()

        self.who_is_context = app_commands.ContextMenu(
            name='Profile',
            callback=self.who_is
        )

        self.bot.tree.add_command(self.who_is_context)

    @app_commands.command(name='points', description='See your current points')
    @app_commands.guild_only()
    async def points(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        await interaction.response.send_message(
            f'Current {server.points_name.capitalize()}: **{member.points:,}**\n'
            f'Activity {server.points_name.capitalize()}: **{member.activity_points:,}**\n'
            f'Pending Payment: **{member.unpaid_ap}**',
            ephemeral=True
        )

    @app_commands.command(name='leaderboard', description='See a top 10 leaderboard')
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        members = list(server.members.members.values())
        member = server.members.get(interaction.user.id)
        leaderboard_string = build_leaderboard(member, members, lambda x: x.activity_points)
        a_embed = discord.Embed(
            colour=member.colour(),
            title=f'{member.guild.name} Activity Leaderboard',
            description=f'```{leaderboard_string}```'
        )
        leaderboard_string = build_leaderboard(member, members, lambda x: x.points)
        p_embed = discord.Embed(
            colour=member.colour(),
            title=f'{member.guild.name} {server.points_name.capitalize()} Leaderboard',
            description=f'```{leaderboard_string}```'
        )
        await interaction.response.send_message(embeds=[a_embed, p_embed])

    @app_commands.command(name='shop', description='View the shop to spend points')
    @app_commands.guild_only()
    async def shop(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        embed = discord.Embed(
            title=f'{interaction.guild.name} Shop',
            colour=helios.Colour.helios(),
            description='Available Items'
        )
        [embed.add_field(name=x.name, value=x.desc, inline=False) for x in server.shop.items]
        view = ShopView(server)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name='play', description='Play or queue music.')
    @app_commands.describe(song='Must be a full youtube URL, including the https://')
    @app_commands.guild_only()
    async def play_command(self, interaction: discord.Interaction, song: str):
        server = self.bot.servers.get(interaction.guild_id)
        await server.music_player.member_play(interaction, song)

    async def who_is(self, interaction: discord.Interaction, member: discord.Member):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(member.id)
        await interaction.response.send_message(embed=member.profile(), ephemeral=True)

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=datetime.utcnow().astimezone().tzinfo))
    async def pay_ap(self):
        tsks = []
        saves = []
        for server in self.bot.servers.servers.values():
            for member in server.members.members.values():
                tsks.append(member.payout_activity_points())
            saves.append(server.members.save_all())
        if tsks:
            await asyncio.gather(*tsks)
            await asyncio.gather(*saves)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(PointsCog(bot))
