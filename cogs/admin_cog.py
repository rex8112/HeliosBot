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
import discord
from discord import app_commands
from discord.ext import commands
from typing_extensions import Literal

from helios import Blackjack, Items
from helios.shop import *

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember


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

    @app_commands.command(name='add_action_token', description='Add an action token to a user')
    @commands.has_permissions(administrator=True)
    async def add_action_token(self, interaction: discord.Interaction, target: discord.Member, token: Literal['mute', 'deafen'], quantity: int = 1):
        server = self.bot.servers.get(interaction.guild_id)
        target_member = server.members.get(target.id)
        item = Items.action_token(token)
        await target_member.inventory.add_item(item, quantity)
        await interaction.response.send_message(f'Added {quantity} action token to {target.display_name}', ephemeral=True)

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


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(AdminCog(bot))
