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
from typing import TYPE_CHECKING

import discord.ui

if TYPE_CHECKING:
    from ..helios_bot import HeliosBot


__all__ = ('StartBlackjackView',)


class StartBlackjackView(discord.ui.View):
    def __init__(self, bot: 'HeliosBot'):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='Start Blackjack', style=discord.ButtonStyle.green, custom_id='helios:gambling:blackjack:start')
    async def start_blackjack(self, interaction: discord.Interaction, button: discord.ui.Button):
        server = self.bot.servers.get(interaction.guild_id)
        channel = interaction.channel
        if not server.gambling.can_run_blackjack(channel):
            await interaction.response.send_message('A blackjack game is already running in this channel.', ephemeral=True)
            return
        await interaction.response.send_message('Starting blackjack game...', ephemeral=True)
        if interaction.message:
            try:
                await interaction.message.delete()
            except discord.HTTPException:
                ...
        await server.gambling.run_blackjack(channel)
