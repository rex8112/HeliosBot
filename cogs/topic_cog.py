from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from helios import TopicCreation

if TYPE_CHECKING:
    from helios import HeliosBot


class TopicCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='topic', description='Create a new topic')
    async def topic_create(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TopicCreation())


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(TopicCog(bot))
