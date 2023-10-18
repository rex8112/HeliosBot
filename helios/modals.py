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

import traceback
from typing import TYPE_CHECKING

from discord import ui, Interaction

if TYPE_CHECKING:
    from .server import Server
    from .helios_bot import HeliosBot
    from .channel import VoiceChannel


class TopicCreation(ui.Modal, title='New Topic'):
    name = ui.TextInput(label='Name')

    async def on_submit(self, interaction: Interaction) -> None:
        bot: 'HeliosBot' = interaction.client
        server: 'Server' = bot.servers.get(interaction.guild_id)
        result, result_message = await server.channels.create_topic(self.name.value, interaction.user)
        await interaction.response.send_message(result_message, ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        traceback.print_exc()
        await interaction.response.send_message('Sorry, something went wrong.', ephemeral=True)


class VoiceNameChange(ui.Modal, title='Change Name'):
    name = ui.TextInput(label='Name', min_length=3, max_length=25)

    def __init__(self, voice: 'VoiceChannel'):
        super().__init__()
        self.voice = voice

    async def on_submit(self, interaction: Interaction) -> None:
        for template in self.voice.owner.templates:
            if template.name.lower() == self.name.value.lower():
                await interaction.response.send_message(
                    'You already have a template with this name!',
                    ephemeral=True
                )
                return
        await self.voice.change_name(self.name.value)

    async def on_error(self, interaction: Interaction,
                       error: Exception) -> None:
        await interaction.response.send_message('Sorry, something went wrong.',
                                                ephemeral=True)
