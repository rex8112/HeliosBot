#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
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
import asyncio
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from typing_extensions import Literal

from helios import Blackjack, Items
from helios.shop import *
from helios.database import StatisticModel

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember

@app_commands.guild_only()
class AdminToggleCog(commands.GroupCog, name='toggle'):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='admin', description='Toggle your own powers')
    async def toggle(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        inactive: discord.Role = server.settings.inactive_admin.value
        active = server.settings.active_admin.value
        if inactive is None or active is None:
            return await interaction.response.send_message('This is not setup', ephemeral=True)
        if inactive in interaction.user.roles:
            if active in interaction.user.roles:
                await interaction.user.remove_roles(active)
                await interaction.response.send_message('You are now inactive', ephemeral=True)
            else:
                await interaction.user.add_roles(active)
                await interaction.response.send_message('You are now active', ephemeral=True)
        else:
            await interaction.response.send_message('You are not an admin', ephemeral=True)
            return


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class AdminCog(commands.GroupCog, name='admin'):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='change_points', description='See your current points')
    @commands.has_permissions(administrator=True)
    @app_commands.describe(target='Member to change points for',
                           points='Amount of points to add or remove, supports negative numbers',
                           description='Reason for changing points',
                           announce='Whether to announce the change to the target')
    async def points(self, interaction: discord.Interaction, target: discord.Member, points: int, description: str = '',
                     announce: bool = False):
        server = self.bot.servers.get(interaction.guild_id)
        target_member = server.members.get(target.id)
        await target_member.add_points(points, 'Helios', f'ADMIN {interaction.user.name[:10]}: {description}')
        await target_member.save()
        await interaction.response.send_message(
            f'Added {points} points to {target.display_name}',
            ephemeral=True
        )

        if announce:
            embed = discord.Embed(
                title=f'{server.points_name.capitalize()} Changed',
                description=f'Your {server.points_name} have been changed by **{points}** by an admin. You now have '
                            f'**{target_member.points}** {server.points_name.capitalize()}\n\nReason: {description}',
                color=discord.Color.red()
            )
            try:
                await target.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @app_commands.command(name='reset_dynamic_voice', description='Reset a dynamic voice channel')
    @commands.has_permissions(manage_channels=True)
    async def reset_dynamic_voice(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        server = self.bot.servers.get(interaction.guild_id)
        if channel.id not in server.channels.dynamic_voice.channels:
            await interaction.response.send_message('This channel is not a dynamic voice channel.', ephemeral=True)
            return
        if channel.members:
            new_channel: Optional[discord.VoiceChannel] = discord.utils.find(lambda x: len(x.channel.members) == 0,
                                                                             await server.channels.dynamic_voice.get_active())
            for member in channel.members:
                if new_channel:
                    await member.edit(voice_channel=new_channel)
                else:
                    await member.edit(voice_channel=None)
        await interaction.response.defer(ephemeral=True)
        await server.channels.dynamic_voice.reset_channel(channel)
        await interaction.followup.send(content='Channel reset.')

    @app_commands.command(name='add_gamble_credit', description='Add credit to a user')
    @commands.has_permissions(administrator=True)
    async def add_gamble_credit(self, interaction: discord.Interaction, target: discord.Member, amount: int, quantity: int = 1):
        server = self.bot.servers.get(interaction.guild_id)
        target_member = server.members.get(target.id)
        item = Items.gamble_credit(amount)
        await target_member.inventory.add_item(item, quantity)
        await interaction.response.send_message(f'Added {amount} gamble credit to {target.display_name}', ephemeral=True)

    @app_commands.command(name='add_token', description='Add an action token to a user')
    @commands.has_permissions(administrator=True)
    async def add_token(self, interaction: discord.Interaction, target: discord.Member, token: Literal['mute', 'deafen'], quantity: int = 1):
        server = self.bot.servers.get(interaction.guild_id)
        target_member = server.members.get(target.id)
        if token == 'mute':
            item = Items.mute_token()
        elif token == 'deafen':
            item = Items.deafen_token()
        await target_member.inventory.add_item(item, quantity)
        await interaction.response.send_message(f'Added {quantity} {item.display_name} to {target.display_name}',
                                                ephemeral=True)

    @app_commands.command(name='edit_store', description='Edit the store')
    @commands.has_permissions(administrator=True)
    async def edit_store(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        view = server.store.get_edit_view()
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

    @app_commands.command(name='refresh_tdescriptions', description='Refreshes all topic descriptions')
    @commands.has_permissions(manage_channels=True)
    async def refresh_desc(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        server = self.bot.servers.get(interaction.guild_id)
        for topic in server.channels.topic_channels.values():
            if topic.channel.topic != topic.get_description():
                await topic.channel.edit(topic=topic.get_description())
        await interaction.followup.send(content='Finished')

    @app_commands.command(name='other', description='Other commands')
    @commands.has_permissions(administrator=True)
    async def other(self, interaction: discord.Interaction, command: str, arg: str):
        if command == 'bust':
            server = self.bot.servers.get(interaction.guild_id)
            games = filter(lambda x: isinstance(x, Blackjack) and x.id == int(arg), server.gambling.games)
            game: Optional[Blackjack] = next(games, None)
            if game:
                game.force_bust = True
                await interaction.response.send_message('Will bust dealer', ephemeral=True)
            else:
                await interaction.response.send_message('Game not found', ephemeral=True)
        elif command == 'stat_record':
            await interaction.response.defer(ephemeral=True)
            await StatisticModel.record_all()
            await interaction.followup.send('Finished')
        elif command == 'stat_24hr':
            await interaction.response.defer(ephemeral=True)
            dt = datetime.now().astimezone() - timedelta(days=1)
            server = self.bot.servers.get(interaction.guild_id)
            member = server.members.get(interaction.user.id)
            embed = discord.Embed(
                title=f'Statistics for {member.member.display_name}',
                color=discord.Color.blue()
            )
            description = 'Last 24 hours'
            for stat in member.statistics.all_stats():
                value = await stat.get_change_since(dt)
                description += f'\n**{stat.display_name}**: {value}'
            embed.description = description
            await interaction.followup.send(embed=embed)
        elif command == 'migrate_ap':
            await interaction.response.defer(ephemeral=True)
            tasks = []
            for server in self.bot.servers.servers.values():
                for member in server.members.members.values():
                    ap = member.db_entry.activity_points
                    if ap > 0:
                        await member.statistics.voice_time.increment(ap)
                        member.db_entry.activity_points = 0
                        tasks.append(member.db_entry.async_save(only=['activity_points']))

            await asyncio.gather(*tasks)
            await interaction.followup.send('Finished')


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(AdminToggleCog(bot))
    await bot.add_cog(AdminCog(bot))
