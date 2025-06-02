#  MIT License
#
#  Copyright (c) 2025 Riley Winkler
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
from discord import ui

from ..theme import Theme, ThemeRole
from ..tools.modals import get_simple_modal

if TYPE_CHECKING:
    from ..server import Server
    from ..member import HeliosMember

__all__ = ('ThemeEditView', 'RoleEditView')

class ThemeEditView(ui.View):
    def __init__(self, server: 'Server', author: 'HeliosMember', theme: 'Theme' = None, *, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.server = server
        self.author = author
        if theme is None:
            theme = Theme(server, name='', roles=[])
            theme.owner = author
            self.new = True
        else:
            self.new = False
        self.theme = theme
        self.update_buttons()

    def update_buttons(self):
        # Role Selection
        options = [discord.SelectOption(label=role.name, value=str(i)) for i, role in enumerate(self.theme.roles)]
        options.append(discord.SelectOption(label='Add New Role', value='new'))
        self.edit_role.options = options
        if self.new:
            self.save_close.label = 'Create & Close'

    async def update_message(self, interaction: discord.Interaction):
        self.update_buttons()
        embed = self.get_embed()
        await interaction.edit_original_response(embeds=[embed], view=self)

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.theme.name if self.theme.name else 'New Theme',
        )
        desc = f'By {self.theme.owner.member.mention}\n' if self.theme.owner else 'No owner set\n'
        for role in self.theme.roles:
            desc += f'\n**{role.name}** - Max: {role.maximum} - {role.color}'
        embed.description = desc
        if not self.new:
            embed.set_footer(text='Changes are saved automatically on existing themes.')
        if self.theme.banner_url:
            embed.set_image(url=self.theme.banner_url)

        return embed

    @ui.select(placeholder='Add/Edit Role', min_values=1, max_values=1)
    async def edit_role(self, interaction: discord.Interaction, select: ui.Select):
        if select.values[0] == 'new':
            last_max = self.theme.roles[-1].maximum if self.theme.roles else 1
            role = ThemeRole(name='', color='#000000', maximum=last_max)
            new = True
        else:
            role_index = int(select.values[0])
            role = self.theme.roles[role_index]
            new = False
        view = RoleEditView(role, timeout=self.timeout)
        await interaction.response.edit_message(embeds=view.get_embeds(), view=view)
        if await view.wait():
            return
        if new and role.name:
            self.theme.roles.append(role)
        await self.update_message(interaction)
        if not self.new:
            await self.theme.save()

    @ui.button(label='Change Theme Name', style=discord.ButtonStyle.primary)
    async def change_name_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Theme Name', 'Theme Name', max_length=25)
        modal = modal_cls(default=self.theme.name)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        if not modal.value:
            await interaction.followup.send('Theme name cannot be empty.', ephemeral=True)
            return
        self.theme.name = modal.value
        await self.update_message(interaction)
        if not self.new:
            await self.theme.save()

    @ui.button(label='Set Banner URL', style=discord.ButtonStyle.primary)
    async def set_banner_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Set Theme Banner URL', 'Banner URL', max_length=255)
        modal = modal_cls(default=self.theme.banner_url)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        if not modal.value:
            self.theme.banner_url = None
        else:
            self.theme.banner_url = modal.value
        await self.update_message(interaction)
        if not self.new:
            await self.theme.save()

    @ui.button(label='Close', style=discord.ButtonStyle.green)
    async def save_close(self, interaction: discord.Interaction, button: ui.Button):
        if self.new:
            # First save just to create the theme, second save needs to happen for more detailed info
            await self.theme.save()
            self.new = False
        await self.theme.save()
        await interaction.response.edit_message(content='Theme saved successfully!', view=None, embeds=[], delete_after=5)
        self.stop()


class RoleEditView(ui.View):
    def __init__(self, role: 'ThemeRole', *, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.role = role
        self.error_message = None

    def get_embeds(self) -> list[discord.Embed]:
        embeds = []
        if self.error_message:
            embed = discord.Embed(
                title='Error',
                description=self.error_message,
                color=discord.Color.red()
            )
            embeds.append(embed)

        embed = discord.Embed(
            title='Edit Role',
            description=f'Editing role: **{self.role.name}**\n'
                        f'Color: {self.role.color}\n'
                        f'Maximum: {self.role.maximum}',
            color=discord.Color.from_str(self.role.color)
        )
        if self.role.icon_url:
            embed.set_thumbnail(url=self.role.icon_url)
        embeds.append(embed)
        return embeds

    @ui.button(label='Change Name', style=discord.ButtonStyle.primary)
    async def change_name_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Role Name', 'Name')
        modal = modal_cls(default=self.role.name)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        if not modal.value:
            self.error_message = 'Role name cannot be empty.'
        else:
            self.role.name = modal.value
            self.error_message = None
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Change Color', style=discord.ButtonStyle.primary)
    async def change_color_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Role Color', 'Color (hex)')
        modal = modal_cls(default=self.role.color)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        try:
            color = discord.Color.from_str(modal.value)
            self.role.color = str(color)
            self.error_message = None
        except ValueError:
            self.error_message = 'Invalid color format. Please use a valid hex color code.'
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Change Maximum', style=discord.ButtonStyle.primary)
    async def change_maximum_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Role Maximum', 'Maximum')
        modal = modal_cls(default=str(self.role.maximum))
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        try:
            maximum = int(modal.value)
            if maximum <= 0:
                self.error_message = 'Maximum must be a positive number. If this is the bottom most role it will be unlimited no matter what and you can set this to whatever.'
            else:
                self.role.maximum = maximum
                self.error_message = None
        except ValueError:
            self.error_message = 'Invalid maximum value. Please enter a valid number.'
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Change Icon', style=discord.ButtonStyle.primary)
    async def change_icon_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Role Icon', 'Icon URL', max_length=255)
        modal = modal_cls(default=self.role.icon_url)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        if not modal.value:
            self.error_message = 'Role icon URL cannot be empty. Use "None" to remove the icon.'
        else:
            if modal.value.lower() == 'none':
                self.role.icon_url = None
            else:
                self.role.icon_url = modal.value
            self.error_message = None
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Close', style=discord.ButtonStyle.gray)
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.stop()
