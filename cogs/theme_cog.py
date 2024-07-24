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

import logging
import traceback
from datetime import time, datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands, Interaction, ui
from discord.ext import commands, tasks

from helios import DynamicVoiceGroup, VoiceManager, PaginatorSelectView

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember


logger = logging.getLogger('Helios.ThemeCog')


def get_change_str(changes: list[tuple['HeliosMember', discord.Role, discord.Role]]) -> str:
    ch_str = ''
    last_to_role = None
    for change in changes:
        if last_to_role != change[2]:
            last_to_role = change[2]
            ch_str += f'### New {last_to_role.mention} Member(s)\n'
        ch_str += f'{change[0].member.mention}\n-# From {change[1].mention if change[1] else "None"}\n'
    return ch_str


class ThemeCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.sort_themes.start()

    async def cog_unload(self) -> None:
        ...

    @app_commands.command(name='build_theme', description='Build a new theme with current roles')
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def build_theme(self, interaction: discord.Interaction):
        """Build a new theme with current roles."""
        server = self.bot.servers.get(interaction.guild_id)
        tm = server.theme
        view = SelectRoleView(interaction.user)
        await interaction.response.send_message('Select roles to include in the theme.', view=view, ephemeral=True)
        if await view.wait():
            return
        roles = view.roles
        await tm.build_theme(roles)
        await interaction.edit_original_response(content='Theme built.', view=None)

    @app_commands.command(name='sort_theme', description='Sort members by theme')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_roles=True)
    async def sort_theme(self, interaction: discord.Interaction):
        """Sort members by theme."""
        server = self.bot.servers.get(interaction.guild_id)
        tm = server.theme
        await interaction.response.defer(ephemeral=True)
        changes = await tm.sort_members()
        if changes:
            logger.info(f'Sorted {len(changes)} member(s) on {server.name}.')
            changes_str = get_change_str(changes)
            embed = discord.Embed(
                title='Role Changes',
                description=changes_str,
                colour=discord.Colour.blurple()
            )
            await interaction.followup.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        else:
            await interaction.followup.send('No changes were made.')

    @tasks.loop(time=time(hour=0, minute=5, tzinfo=datetime.now().astimezone().tzinfo))
    async def sort_themes(self):
        for server in self.bot.servers.servers.values():
            tm = server.theme
            changes = await tm.sort_members()
            if changes:
                logger.info(f'Sorted {len(changes)} members on {server.name}.')
                logger.info(f'Sorted {len(changes)} member(s) on {server.name}.')
                changes_str = get_change_str(changes)
                embed = discord.Embed(
                    title='Role Changes',
                    description=changes_str,
                    colour=discord.Colour.blurple()
                )
                if server.announcement_channel:
                    await server.announcement_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())


class SelectRoleView(ui.View):
    def __init__(self, author: discord.Member):
        super().__init__()
        self.author = author
        self.roles = []

    @ui.select(placeholder='Select Roles', min_values=1, max_values=10, cls=ui.RoleSelect)
    async def select_roles(self, interaction: Interaction, select: ui.RoleSelect):
        roles = select.values
        roles = sorted(roles, key=lambda x: x, reverse=True)
        self.roles = roles
        await interaction.response.send_message(f'Selected roles: {", ".join([x.name for x in roles])}',
                                                ephemeral=True)
        self.stop()


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(ThemeCog(bot))
