from typing import Optional, Callable

import discord

from .modals import SearchModal


class YesNoView(discord.ui.View):
    def __init__(self, author: discord.Member, *, timeout=5):
        super().__init__(timeout=timeout)
        self.author = author
        self.value = None

    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction,
                  button: discord.ui.Button):
        if interaction.user == self.author:
            self.value = True
            await interaction.response.defer()
            self.stop()
        else:
            await interaction.response.send_message('You are not allowed to '
                                                    'respond',
                                                    ephemeral=True)

    @discord.ui.button(label='No', style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction,
                 button: discord.ui.Button):
        if interaction.user == self.author:
            self.value = False
            await interaction.response.defer()
            self.stop()
        else:
            await interaction.response.send_message('You are not allowed to '
                                                    'respond',
                                                    ephemeral=True)


class SelectMemberView(discord.ui.View):
    def __init__(self, author: discord.Member, *, max_select: int = 1, min_select: int = 1,
                 timeout: Optional[int] = 60, check: Callable[[discord.Member], tuple[bool, str]] = None):
        super().__init__(timeout=timeout)
        self.author = author
        self.max_select = max_select
        self.min_select = min_select
        self.check = check
        self.current_search = None
        self.selected = None

    @discord.ui.select(cls=discord.ui.UserSelect)
    async def select_member(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if self.author != interaction.user:
            await interaction.response.send_message('You are not allowed to use this.', ephemeral=True)
            return
        
        values = select.values
        if self.check:
            allowed = filter(lambda x: self.check(x)[0], values)
            if allowed:
                self.selected = allowed
            else:
                await interaction.response.send_message('No Valid Selections', ephemeral=True)
                return
        else:
            self.selected = values
        await interaction.response.defer()
        self.stop()
