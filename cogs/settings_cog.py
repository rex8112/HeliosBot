from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from helios import HeliosBot


class SettingsCog(commands.GroupCog, name='settings'):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        super().__init__()

    @app_commands.command(name='topiccategory', description='Set the topic category')
    @app_commands.checks.has_permissions(administrator=True)
    async def topic_category(self, interaction: discord.Interaction, topic_category: discord.CategoryChannel):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        server.settings.topic_category = topic_category.id
        await server.save()
        await interaction.response.send_message('Setting Changed', ephemeral=True)

    @app_commands.command(name='archivecategory', description='Set the archive category')
    @app_commands.checks.has_permissions(administrator=True)
    async def archive_category(self, interaction: discord.Interaction, archive_category: discord.CategoryChannel):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        server.settings.archive_category = archive_category.id
        await server.save()
        await interaction.response.send_message('Setting Changed', ephemeral=True)

    @app_commands.command(name='privatecategory',
                          description='Set the private voice category')
    @app_commands.checks.has_permissions(administrator=True)
    async def archive_category(self, interaction: discord.Interaction,
                               private_channel: discord.VoiceChannel):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        server.settings.private_create = private_channel
        await server.save()
        await interaction.response.send_message('Setting Changed',
                                                ephemeral=True)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(SettingsCog(bot))
