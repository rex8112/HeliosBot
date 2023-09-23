from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from helios import HeliosBot, Server


class PointsCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='points', description='See your current points')
    @app_commands.guild_only()
    async def points(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        await interaction.response.send_message(
            f'Current Points: **{member.activity_points:,}**',
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
            leaderboard_string += f'{modifier:1}{i:2}. {mem.member.display_name:>32}: {mem.activity_points:10,}\n'
        if not user_found:
            i = members.index(member)
            leaderboard_string += '...\n'
            for i, mem in enumerate(members[i-1:i+1], start=i):
                modifier = ''
                if mem.member == interaction.user:
                    modifier = '>'
                leaderboard_string += f'{modifier:1}{i:2}. {mem.member.display_name:>32}: {mem.activity_points:10,}\n'
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


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(PointsCog(bot))