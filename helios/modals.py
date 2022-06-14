from discord import ui, Interaction


class TopicCreation(ui.Modal, title='New Topic'):
    name = ui.TextInput(label='Name')

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(f'Wowie', ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await interaction.response.send_message('Sorry, something went wrong.', ephemeral=True)
