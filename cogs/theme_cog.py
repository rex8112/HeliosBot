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
from datetime import time, datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands, Interaction, ui
from discord.ext import commands, tasks

from helios import ThemeEditView, ThemeSelectView

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


# noinspection PyUnresolvedReferences
class ThemeCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.sort_themes.start()

        self.lb_view = LeaderboardView(self.bot)
        self.bot.add_view(self.lb_view)

    async def cog_unload(self) -> None:
        self.lb_view.stop()

    @app_commands.command(name='leaderboard', description='Leaderboard of current points.')
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        theme = server.theme.current_theme
        if theme is None:
            return await interaction.response.send_message('No theme is currently active so no leaderboard can be made.', ephemeral=True)
        embeds = await theme.get_leaderboard_embeds(member)

        await interaction.response.send_message(embeds=embeds, ephemeral=True)

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

    @app_commands.command(name='themes', description='Create/Edit/View themes.')
    @app_commands.guild_only()
    @app_commands.describe(edit_theme='Quickly edit a theme by name.')
    async def themes(self, interaction: discord.Interaction, edit_theme: str = None):
        """Create/Edit/View themes."""
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        if edit_theme:
            theme = await server.theme.get_theme(edit_theme.lower())
            if theme is None:
                return await interaction.response.send_message('Theme not found.', ephemeral=True)
            view = ThemeEditView(server, theme, member)
            await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)
            return
        themes = await server.theme.get_themes()
        view = ThemeSelectView(server, themes, member)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

    @app_commands.command(name='apply_theme', description='Apply a theme to your server.')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def apply_theme(self, interaction: discord.Interaction, theme: str):
        server = self.bot.servers.get(interaction.guild_id)
        tm = server.theme
        theme = await tm.get_theme(theme.lower())
        if theme is None:
            return await interaction.response.send_message('Theme not found.', ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await tm.apply_theme(theme)
        await interaction.followup.send(f'Applied theme **{theme.name}** to the server.')

    @tasks.loop(time=time(hour=0, minute=5, tzinfo=datetime.now().astimezone().tzinfo))
    async def sort_themes(self):
        for server in self.bot.servers.servers.values():
            tm = server.theme
            changes = await tm.sort_members()
            if server.announcement_channel:
                if changes:
                    logger.info(f'Sorted {len(changes)} member(s) on {server.name}.')
                    changes_str = get_change_str(changes)
                    embed = discord.Embed(
                        title='Role Changes',
                        description=changes_str,
                        colour=discord.Colour.blurple()
                    )
                    if server.announcement_channel:
                        await server.announcement_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none(), view=self.lb_view)
                        #embeds = get_leaderboard_embeds(server)
                        #await server.announcement_channel.send(embeds=embeds, view=self.lb_view)


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
class LeaderboardView(ui.View):
    def __init__(self, bot: 'HeliosBot'):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label='Show Me!', custom_id='leaderboard.showme', style=discord.ButtonStyle.green)
    async def show_me(self, interaction: Interaction, _: ui.Button):
        server = self.bot.servers.get(interaction.guild_id)
        theme = server.theme.current_theme
        if theme is None:
            return await interaction.response.send_message('No theme is currently active so no leaderboard can be made.', ephemeral=True)
        member = server.members.get(interaction.user.id)
        embeds = theme.get_leaderboard_embeds(server, member, only_member=True)
        await interaction.response.send_message(embeds=embeds, ephemeral=True)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(ThemeCog(bot))
