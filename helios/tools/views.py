from typing import Optional, Callable, Any, TypeVar, Hashable

import discord

from .modals import SearchModal, PageModal


class YesNoView(discord.ui.View):
    def __init__(self, author: discord.Member, *, timeout=5):
        super().__init__(timeout=timeout)
        self.author: discord.Member = author
        self.value: Optional[bool] = None

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
        self.selected: list[discord.Member] = []

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


T = TypeVar('T', bound=Hashable)


class PaginatorView(discord.ui.View):
    def __init__(self, values: list[T], get_embeds: Callable[[list[T]], list[discord.Embed]], /,
                 page_size: int = 10, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.values = values
        self.get_embeds = get_embeds
        self.page_size = page_size
        self.page = 0
        self.update_buttons()

    @property
    def last_page(self):
        return int(len(self.values) // self.page_size)

    def get_paged_values(self) -> list[T]:
        page_size = self.page_size
        page_index = page_size * (self.page + 1)
        return self.values[self.page*page_size:page_index]

    def update_buttons(self):
        self.first.disabled = False
        self.previous.disabled = False
        self.next.disabled = False
        self.last.disabled = False

        self.select.label = f'{self.page+1}/{self.last_page+1}'

        if self.page == 0:
            self.first.disabled = True
            self.previous.disabled = True
        if self.page == self.last_page:
            self.next.disabled = True
            self.last.disabled = True

    @discord.ui.button(label='<<', style=discord.ButtonStyle.grey)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embeds=self.get_embeds(self.get_paged_values()), view=self)

    @discord.ui.button(label='<', style=discord.ButtonStyle.grey)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(self.page - 1, 0)
        self.update_buttons()
        await interaction.response.edit_message(embeds=self.get_embeds(self.get_paged_values()), view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey)
    async def select(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PageModal(default=self.page+1)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        self.page = modal.page_selected - 1
        self.update_buttons()
        await interaction.edit_original_response(embeds=self.get_embeds(self.get_paged_values()), view=self)

    @discord.ui.button(label='>', style=discord.ButtonStyle.grey)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(self.page + 1, self.last_page)
        self.update_buttons()
        await interaction.response.edit_message(embeds=self.get_embeds(self.get_paged_values()), view=self)

    @discord.ui.button(label='>>', style=discord.ButtonStyle.grey)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = self.last_page
        self.update_buttons()
        await interaction.response.edit_message(embeds=self.get_embeds(self.get_paged_values()), view=self)


class PaginatorSelectView(PaginatorView):
    def __init__(self, values: dict[T, str], get_embeds: Callable[[list[T]], list[discord.Embed]], /,
                 page_size: int = 10, timeout: int = 180):
        self.values_string = list(values.values())
        self.selected: Optional[T] = None
        super().__init__(list(values.keys()), get_embeds, page_size=page_size, timeout=timeout)

    def update_options(self):
        values = self.get_paged_values()
        options = []
        for value in values:
            label = self.values_string[self.values.index(value)]
            options.append(discord.SelectOption(label=label))
        return options

    def update_buttons(self):
        super().update_buttons()
        self.select_item.options = self.update_options()

    @discord.ui.select()
    async def select_item(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        self.selected = self.values[self.values_string.index(select.values[0])]
        self.stop()
