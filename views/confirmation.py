# A simple confirmation View
from typing import Optional, Union
import discord
from discord.ext import commands


class ConfirmationView(discord.ui.View):
    """A simple confirmation View"""
    def __init__(self, default: bool = False, author: Optional[Union[discord.User, discord.Member]] = None):
        super().__init__()
        self.author: Optional[Union[discord.User, discord.Member]] = author
        self.confirmed: bool = default

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author:
            return interaction.user == self.author
        return True

    async def wait_for_answer(self):
        await self.wait()
        return self.confirmed

    def disable_buttons(self):
        for b in filter(lambda x: isinstance(x, discord.ui.Button), self.children):
            b.disabled = True

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.confirmed = True
        self.disable_buttons()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.confirmed = False
        self.disable_buttons()
        await interaction.response.edit_message(view=self)
        self.stop()