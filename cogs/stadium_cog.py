import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from helios import HeliosBot


class StadiumCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='points', description='See your current points')
    async def points(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        await interaction.response.send_message(
            f'Current Points: **{member.points:,}**\nActivity Points: **{member.activity_points:,}**',
            ephemeral=True
        )

    @app_commands.command(name='daily', description='Claim daily points')
    async def daily(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        if member.claim_daily():
            await interaction.response.defer(ephemeral=True)
            await member.save()
            await interaction.followup.send(f'Claimed **{server.stadium.daily_points:,}** points!')
        else:
            epoch_time = server.stadium.epoch_day.time()
            tomorrow = datetime.datetime.now().astimezone() + datetime.timedelta(days=1)
            tomorrow = tomorrow.date()
            tomorrow = datetime.datetime.combine(tomorrow, epoch_time)
            await interaction.response.send_message(f'Check back <t:{tomorrow.timestamp()}:R>', ephemeral=True)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(StadiumCog(bot))
