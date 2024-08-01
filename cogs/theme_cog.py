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
from typing import TYPE_CHECKING, Callable

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


def get_leaderboard_string(num: int, member: 'HeliosMember', value: int, prefix: str = ''):
    return f'{prefix:2}{num:3}. {member.member.display_name:>32}: {value:10,}\n'


def build_leaderboard(author: 'HeliosMember', member_pos: list[tuple['HeliosMember', int]]) -> str:
    leaderboard_string = ''
    user_found = False
    for mem, pos in member_pos[:10]:
        modifier = ''
        if mem == author:
            modifier = '>'
            user_found = True
        leaderboard_string += get_leaderboard_string(pos+1, mem, mem.points, modifier)
    mem_only = [x[0] for x in member_pos]
    if not user_found and author in mem_only:
        index = mem_only.index(author)
        leaderboard_string += '...\n'
        for mem, i in member_pos[index - 1:index + 2]:
            modifier = ''
            if mem == author:
                modifier = '>'
            leaderboard_string += get_leaderboard_string(i, mem, key(mem), modifier)
    return leaderboard_string


class ThemeCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.sort_themes.start()

    async def cog_unload(self) -> None:
        ...

    @app_commands.command(name='leaderboard', description='Leaderboard of current points.')
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        theme = server.theme.current_theme
        if theme is None:
            members = [(x, i) for i,x in enumerate(list(server.members.members.values()))]
            leaderboard_string = build_leaderboard(member, members)
            p_embed = discord.Embed(
                colour=member.colour(),
                title=f'{member.guild.name} {server.points_name.capitalize()} Leaderboard',
                description=f'```{leaderboard_string}```'
            )
            return await interaction.response.send_message(embeds=[p_embed])
        members = list(sorted(server.members.members.values(), key=lambda x: -x.points))
        index = 0
        embeds = []
        for role in theme.roles:
            discord_role = server.theme.role_map[role]
            role_members = []
            for i in range(role.maximum):
                role_members.append((members[index], index))
                index += 1
            lb_str = build_leaderboard(member, role_members)
            embed = discord.Embed(
                title=discord_role.name,
                color=discord_role.color,
                description=f'```{lb_str}```'
            )
            embeds.append(embed)

        await interaction.response.send_message(embeds=embeds)

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
