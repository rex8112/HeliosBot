from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from helios import TopicCreation

if TYPE_CHECKING:
    from helios import HeliosBot, Server


class TopicCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='topic', description='Create a new topic')
    async def topic_create(
            self,
            interaction: discord.Interaction,
            channel: Optional[discord.TextChannel] = None,
            tier: Optional[int] = 1
    ):
        if channel:
            if channel.permissions_for(interaction.user).manage_channels:
                bot: 'HeliosBot' = interaction.client
                server: 'Server' = bot.servers.get(interaction.guild_id)
                result, result_message = await server.channels.add_topic(channel, interaction.user, tier)
                await interaction.response.send_message(result_message, ephemeral=True)
            else:
                await interaction.response.send_message(
                    'You do not have permission to do this, try without parameters',
                    ephemeral=True
                )
        else:
            await interaction.response.send_modal(TopicCreation())


async def setup(bot: commands.Bot):
    await bot.add_cog(TopicCog(bot))
