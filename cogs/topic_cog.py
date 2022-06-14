import discord

from discord import app_commands
from discord.ext import commands
from helios import TopicCreation


class TopicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='topic', description='Create a new topic')
    async def topic_create(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TopicCreation())


async def setup(bot: commands.Bot):
    await bot.add_cog(TopicCog(bot))
