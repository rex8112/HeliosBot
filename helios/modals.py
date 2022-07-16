import traceback
from typing import TYPE_CHECKING

from discord import ui, Interaction

if TYPE_CHECKING:
    from .server import Server
    from .channel import VoiceChannel


class TopicCreation(ui.Modal, title='New Topic'):
    name = ui.TextInput(label='Name')

    async def on_submit(self, interaction: Interaction) -> None:
        bot = interaction.client
        server: 'Server' = bot.servers.get(interaction.guild_id)
        result, result_message = await server.channels.create_topic(self.name.value, interaction.user)
        await interaction.response.send_message(result_message, ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        traceback.print_exc()
        await interaction.response.send_message('Sorry, something went wrong.', ephemeral=True)


class VoiceNameChange(ui.Modal, title='Change Name'):
    name = ui.TextInput(label='Name')

    async def on_submit(self, interaction: Interaction) -> None:
        bot = interaction.client
        server: 'Server' = bot.servers.get(interaction.guild_id)
        channel: 'VoiceChannel' = server.channels.get(interaction.channel_id)
        await channel.change_name(self.name.value)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message('Sorry, something went wrong.', ephemeral=True)
