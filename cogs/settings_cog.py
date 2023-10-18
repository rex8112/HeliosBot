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

from typing import TYPE_CHECKING, Optional

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

    @app_commands.command(
        name='stadiumcategory',
        description='Setting this will enable the stadium. This is irreversible.')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        new='Whether to create a new category or use an existing one. Requires category to be set if false.')
    async def stadium_category(
            self,
            interaction: discord.Interaction,
            new: bool,
            stadium_category: Optional[discord.CategoryChannel]):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        stadium = server.stadium
        if not new:
            if stadium_category:
                stadium.settings['category'] = stadium_category
            else:
                raise AttributeError('stadium_category is required if new is False')
        else:
            overwrites = {
                server.guild.me: discord.PermissionOverwrite(
                    send_messages=True,
                    create_private_threads=True,
                    create_public_threads=True
                ),
                server.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False,
                    send_messages_in_threads=True,
                    create_private_threads=False,
                    create_public_threads=False
                )
            }
            sc = await server.guild.create_category('Stadium', reason='Stadium Initialization', overwrites=overwrites)
            stadium.settings['category'] = sc
        await stadium.build_channels()
        await stadium.save()
        if not stadium.running:
            stadium.create_run_task()
        await interaction.response.send_message('Stadium Set', ephemeral=True)

    @app_commands.command(name='privatechannel',
                          description='Set the private voice category')
    @app_commands.checks.has_permissions(administrator=True)
    async def private_channel(self, interaction: discord.Interaction,
                              private_channel: discord.VoiceChannel):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        server.settings.private_create = private_channel
        await server.save()
        await interaction.response.send_message('Setting Changed',
                                                ephemeral=True)

    @app_commands.command(name='verifiedrole',
                          description='Set the role that marks someone as verified')
    @app_commands.checks.has_permissions(administrator=True)
    async def verified_role(self, interaction: discord.Interaction,
                            role: discord.Role):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        server.settings.verified_role = role.id
        await server.save()
        await interaction.response.send_message('Setting Changed',
                                                ephemeral=True)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(SettingsCog(bot))
