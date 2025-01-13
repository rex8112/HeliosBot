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
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from helios import Colour

if TYPE_CHECKING:
    from helios import HeliosBot, Server


class HelpCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='help', description='Learn how to use Helios')
    @app_commands.guild_only()
    async def help(self, interaction: discord.Interaction):
        server = self.bot.servers.get(guild_id=interaction.guild_id)
        h = self.get_help(server)
        view = SelectHelpView(h)
        embed = discord.Embed(title='Help', description='Select a topic to learn more', colour=Colour.helios())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def get_help(self, server: 'Server') -> list[tuple[str, str]]:
        return [
            (
                'Topic Channels',
                'Topic channels are user-created channels that are used to discuss a specific topic. The are sorted by '
                'their activity level. Inactive channels at the bottom are archived and can be restored by anyone by '
                'sending a message. To create a topic channel, use the `/topic new` command but be sure to check the '
                'archive category first. Every active topic channel also has a corresponding role that everyone can '
                'mention. To get the role, go to the channel of interest and use the `/topic subscribe` command. You '
                'can also use the `/topic unsubscribe` command to remove the role. To prevent clutter, the roles are '
                'removed when a channel is archived and restored with its members when the channel is active again. If '
                'you want to mention the role in an archived channel, simply mention me and I will do it for you when '
                'the role is set back up.'
                f'\n\n{server.settings.topic_category.value.mention}\n{server.settings.archive_category.value.mention}'
            ),
            (
                'Dynamic Voice Channels',
                'Dynamic voice channels are automatically created voice channels that allow an empty channel to always '
                'be available without cluttering the server. Dynamic Voice Channels have multiple features that can be '
                'utilized by users, you can find these features in the text channel of the voice channels.\n\nThe main '
                'feature of Dynamic Voice Channels is the ability to convert it into a private channel where you can '
                'build the whitelist or blacklist of users that can join the channel. Clicking the private voice '
                'channel button while in the voice channel will try to convert the channel to a private channel, this '
                'will start a vote if more people are in the channel. If you press the button in a channel you are not '
                'in, I will create a new private channel for you. If you are in a private channel, you can press the '
                'Revert button to convert the channel back to a normal dynamic voice channel.'
                f'\n\n{server.settings.dynamic_voice_category.value.mention}'
            ),
            (
                'Verification',
                'When someone joins the server, they are unable to see any channels until another, verified, member '
                'vouches for them. You can verify someone by either using the `/verify` command or by clicking the '
                'button in the system messages channel.'
            ),
            (
                f'{server.points_name.capitalize()}',
                f'{server.points_name.capitalize()} are the currency of the server. You can earn {server.points_name} '
                f'by being in a voice channel or gambling. You can use {server.points_name} to buy items in the shop '
                f'or transfer them to other members using the `/transfer` command. You can check your balance with the '
                f'`/points` command. Activity {server.points_name} are paid out to normal {server.points_name} daily '
                f'at midnight CT.'
            ),
            (
                'Gambling',
                'Currently, blackjack is the only gambling game available. You can play blackjack with the `/blackjack`'
                ' command or by pressing the start button on the last game. Both of these only work in the blackjack '
                'topic channel. There are powerups you can obtain in loot crates that can be used in blackjack.'
            ),
            (
                'Loot Crates',
                'Loot crates are items that you can open to get random items. You can get loot crates from /daily or '
                'by purchasing them in the shop. You can open a loot crate with the `/lootcrate open` command. You can '
                'view the droprates for loot crates with the `/lootcrate droprates` command.'
            ),
            (
                'Voice Actions',
                'Voice actions are effects you can apply on people in voice channels. They use tokens that you can '
                'obtain from loot crates and the shop. Shields protect you from voice actions, you get a couple '
                'from /daily if you are out.'
            )
        ]

async def setup(bot: 'HeliosBot') -> None:
    await bot.add_cog(HelpCog(bot))

class SelectHelpView(discord.ui.View):
    def __init__(self, options: list[tuple[str, str]]):
        super().__init__()
        self.options = options
        opts = []
        for i, option in enumerate(options):
            opts.append(discord.SelectOption(label=option[0], value=str(i)))
        self.select_help.options = opts

    @discord.ui.select(placeholder='Select a topic', min_values=1, max_values=1)
    async def select_help(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected = self.options[int(select.values[0])]
        embed = discord.Embed(title=selected[0], description=selected[1], colour=Colour.helios())
        await interaction.response.edit_message(embed=embed, view=self)
