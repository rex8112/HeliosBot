import asyncio
from datetime import time, datetime, timezone
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from helios.shop import *

if TYPE_CHECKING:
    from helios import HeliosBot, Server, HeliosMember


def get_leaderboard_string(num: int, member: 'HeliosMember', prefix: str = ''):
    return f'{prefix:2}{num:3}. {member.member.display_name:>32}: {member.activity_points:10,}\n'


class PointsCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.pay_ap.start()

    @app_commands.command(name='points', description='See your current points')
    @app_commands.guild_only()
    async def points(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        await interaction.response.send_message(
            f'Current Points: **{member.points:,}**\n'
            f'Activity Points: **{member.activity_points:,}**',
            ephemeral=True
        )

    @app_commands.command(name='leaderboard', description='See a top 10 leaderboard')
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        members = sorted(server.members.members.values(), key=lambda x: -x.activity_points)
        member = server.members.get(interaction.user.id)
        leaderboard_string = ''
        user_found = False
        for i, mem in enumerate(members[:10], start=1):
            modifier = ''
            if mem.member == interaction.user:
                modifier = '>'
                user_found = True
            leaderboard_string += get_leaderboard_string(i, mem, modifier)
        if not user_found:
            index = members.index(member)
            leaderboard_string += '...\n'
            for i, mem in enumerate(members[index-1:index+1], start=index):
                modifier = ''
                if mem.member == interaction.user:
                    modifier = '>'
                leaderboard_string += get_leaderboard_string(i, mem, modifier)
        colour = discord.Colour.default()
        for role in reversed(member.member.roles):
            if role.colour != discord.Colour.default():
                if server.guild.premium_subscriber_role and role.colour == server.guild.premium_subscriber_role.colour:
                    continue
                colour = role.colour
                break
        embed = discord.Embed(
            colour=colour,
            title=f'{member.guild.name} Leaderboard',
            description=f'```{leaderboard_string}```'
        )
        await interaction.response.send_message(embed=embed)

    @tasks.loop(time=time(hour=0, minute=00, tzinfo=datetime.utcnow().astimezone().tzinfo))
    async def pay_ap(self):
        tsks = []
        saves = []
        for server in self.bot.servers.servers.values():
            for member in server.members.members.values():
                tsks.append(member.payout_activity_points())
            saves.append(server.members.save_all())
        if tsks:
            await asyncio.wait(tsks)
            await asyncio.wait(saves)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(PointsCog(bot))
