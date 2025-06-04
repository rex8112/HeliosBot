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
import peewee
from discord import ui

from ..colour import Colour
from ..dynamic_voice import DynamicVoiceGroup
from ..theme import Theme, ThemeRole
from ..tools.modals import get_simple_modal

if TYPE_CHECKING:
    from ..server import Server
    from ..member import HeliosMember

__all__ = ('ThemeSelectView', 'ThemeEditView', 'RoleEditView', 'GroupEditView')


# noinspection PyUnresolvedReferences
class ThemeSelectView(ui.View):
    def __init__(self, server: 'Server', themes: list[Theme], author: 'HeliosMember', *, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.server = server
        self.themes = themes
        self.author = author
        self.page = 0
        self.page_size = 10
        self.max_page = (len(themes) - 1) // self.page_size
        self.selected_theme = None
        self.update_buttons()

    def get_paged_themes(self) -> list[Theme]:
        start = self.page * self.page_size
        end = start + self.page_size
        return self.themes[start:end]

    def get_embed(self):
        embed = discord.Embed(
            title='Theme Selection',
            description='Select a theme to edit or create a new one.',
            color=Colour.helios()
        )
        if self.selected_theme:
            embed.add_field(name='Selected Theme', value=self.selected_theme.name, inline=False)
        return embed

    def update_buttons(self):
        options = []
        for i, theme in enumerate(self.get_paged_themes(), start=self.page * self.page_size):
            options.append(discord.SelectOption(label=theme.name,
                                                description=f'By {theme.owner.member.display_name if theme.owner else "None"}', value=str(i)))
        if not options:
            options.append(discord.SelectOption(label='No Themes Available', value='-1', default=True))
            self.select_theme.disabled = True
        else:
            self.select_theme.disabled = False
        self.select_theme.options = options
        self.number_page.label = f'{self.page + 1}/{self.max_page + 1}'
        if self.page == 0:
            self.previous_page.disabled = True
        else:
            self.previous_page.disabled = False
        if self.page == self.max_page:
            self.next_page.disabled = True
        else:
            self.next_page.disabled = False
        if not self.selected_theme:
            self.edit_theme.disabled = True
        else:
            self.edit_theme.disabled = False
            if (self.selected_theme.owner and self.selected_theme.owner.id == self.author.id) or self.author.member.guild_permissions.manage_guild:
                self.edit_theme.label = 'Edit Theme'
            else:
                self.edit_theme.label = 'View Theme'

    @classmethod
    async def from_server(cls, server: 'Server', author: 'HeliosMember' = None, *, timeout: float = 600.0) -> 'ThemeSelectView':
        themes = await server.theme.get_themes()
        return cls(server, themes, author, timeout=timeout)

    @ui.select(placeholder='Select a Theme', min_values=1, max_values=1)
    async def select_theme(self, interaction: discord.Interaction, select: ui.Select):
        theme_index = int(select.values[0])
        self.selected_theme = self.themes[theme_index]
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @ui.button(label='<', style=discord.ButtonStyle.gray, row=1)
    async def previous_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @ui.button(label='1', style=discord.ButtonStyle.gray, row=1, disabled=True)
    async def number_page(self, interaction: discord.Interaction, button: ui.Button):
        # This button is just a placeholder to show the current page number
        await interaction.response.defer()

    @ui.button(label='>', style=discord.ButtonStyle.gray, row=1)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        if self.page < self.max_page:
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @ui.button(label='Create Theme', style=discord.ButtonStyle.green, row=2)
    async def create_theme(self, interaction: discord.Interaction, button: ui.Button):
        mem = self.server.members.get(interaction.user.id)
        view = ThemeEditView(self.server, mem)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)

    @ui.button(label='Edit Theme', style=discord.ButtonStyle.blurple, row=2)
    async def edit_theme(self, interaction: discord.Interaction, button: ui.Button):
        if self.selected_theme is None:
            await interaction.response.send_message('No theme selected.', ephemeral=True)
            return
        if interaction.user.id != self.author.id:
            await interaction.response.send_message('You cannot edit this theme.', ephemeral=True)
            return
        view = ThemeEditView(self.server, self.author, self.selected_theme)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


# noinspection PyUnresolvedReferences
class ThemeEditView(ui.View):
    def __init__(self, server: 'Server', author: 'HeliosMember', theme: 'Theme' = None, *, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.server = server
        self.author = author
        if theme is None:
            theme = Theme(server, name='', roles=[], groups=[])
            theme.owner = author
            self.new = True
        else:
            self.new = False
        self.theme = theme
        self.update_buttons()

    def update_buttons(self):
        # Role Selection
        editable = self.theme.editable and (self.author == self.theme.owner or self.author.member.guild_permissions.manage_guild)
        options = [discord.SelectOption(label=role.name, value=str(i)) for i, role in enumerate(self.theme.roles)]
        if editable:
            options.append(discord.SelectOption(label='Add New Role', value='new'))
        self.edit_role.options = options
        options = [discord.SelectOption(label=group.template, value=str(i)) for i, group in enumerate(self.theme.groups)]
        if editable:
            options.append(discord.SelectOption(label='Add New Group', value='new'))
        self.edit_group.options = options
        if not editable:
            self.change_name_button.disabled = True
            self.set_afk_name_button.disabled = True
            self.set_banner_button.disabled = True
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
            maximum = role.maximum if role != self.theme.roles[-1] else 'Unlimited'
            desc += f'\n**{role.name}** - Max: {maximum} - {role.color}'
        desc += '\n\n'
        for group in self.theme.groups:
            maximum = group.max
            desc += f'**{group.template}** - {group.min} to {maximum} channels\n'
        desc += '\n\n'
        desc += f'AFK Channel: **{self.theme.afk_channel}**\n'
        embed.description = desc
        if not self.new:
            embed.set_footer(text='Changes are saved automatically on existing themes.')
        if self.theme.banner_url:
            embed.set_image(url=self.theme.banner_url)

        return embed

    def validate(self):
        if not self.theme.name:
            return 'Theme name cannot be empty.'
        if not self.theme.roles:
            return 'At least one role must be defined.'
        if not self.theme.groups:
            return 'At least one group must be defined.'
        if self.theme.afk_channel is None:
            return 'AFK channel must be set.'
        for role in self.theme.roles:
            if not role.name:
                return 'Role name cannot be empty.'
            if not role.color:
                return 'Role color cannot be empty.'
            if role.maximum <= 0:
                return 'Role maximum must be a positive number.'
        for group in self.theme.groups:
            if not group.template:
                return 'Channel template cannot be empty.'
            if not group.game_template:
                return 'Channel game template cannot be empty.'
            if group.min > group.max:
                return 'Channel minimum cannot be greater than maximum.'
            if group.min_empty > group.max:
                return 'Channel minimum empty cannot be greater than maximum.'
            if group.max <= 0:
                return 'Channel maximum must be a positive number.'
            if group.min_empty > group.min:
                return 'Channel minimum empty cannot be greater than minimum.'
        return None

    @ui.select(placeholder='Add/Edit Role', min_values=1, max_values=1)
    async def edit_role(self, interaction: discord.Interaction, select: ui.Select):
        editable = not self.change_name_button.disabled
        if select.values[0] == 'new':
            last_max = self.theme.roles[-1].maximum if self.theme.roles else 1
            role = ThemeRole(name='', color='#000000', maximum=last_max)
            new = True
        else:
            role_index = int(select.values[0])
            role = self.theme.roles[role_index]
            new = False
        view = RoleEditView(role, timeout=self.timeout)
        if not editable:
            await interaction.response.send_message(embeds=view.get_embeds(), ephemeral=True)
            view.stop()
            return
        await interaction.response.edit_message(embeds=view.get_embeds(), view=view)
        if await view.wait():
            return
        if view.delete:
            if new:
                await self.update_message(interaction)
                return
            if len(self.theme.roles) <= 1:
                return
            self.theme.roles.remove(role)
        elif new and role.name:
            self.theme.roles.append(role)
        await self.update_message(interaction)
        if not self.new:
            await self.theme.save()

    @ui.select(placeholder='Add/Edit Channel Settings', min_values=1, max_values=1)
    async def edit_group(self, interaction: discord.Interaction, select: ui.Select):
        editable = not self.change_name_button.disabled
        if select.values[0] == 'new':
            group = DynamicVoiceGroup(self.server, template='{n}{st} Channel', minimum=3, maximum=10, minimum_empty=2, game_template='{n}. {g}')
            new = True
        else:
            group_index = int(select.values[0])
            group = self.theme.groups[group_index]
            new = False
        view = GroupEditView(group, timeout=self.timeout)
        if not editable:
            await interaction.response.send_message(embeds=view.get_embeds(), ephemeral=True)
            view.stop()
            return
        await interaction.response.edit_message(embeds=view.get_embeds(), view=view)
        if await view.wait():
            return
        if view.delete:
            if new:
                await self.update_message(interaction)
                return
            if len(self.theme.groups) <= 1:
                return
            self.theme.groups.remove(group)
        elif new and group.template:
            self.theme.groups.append(group)
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
        self.theme.name = modal.value.lower()
        await self.update_message(interaction)
        if not self.new:
            await self.theme.save()

    @ui.button(label='Set AFK Name', style=discord.ButtonStyle.primary)
    async def set_afk_name_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Set AFK Channel Name', 'AFK Channel Name', max_length=25)
        modal = modal_cls(default=self.theme.afk_channel)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        if not modal.value:
            return
        else:
            self.theme.afk_channel = modal.value
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
            error = self.validate()
            if error:
                await interaction.response.send_message(error, ephemeral=True)
                return
            try:
                await self.theme.save()
            except peewee.IntegrityError:
                await interaction.response.send_message('Theme with this name already exists. Please choose a different name.', ephemeral=True)
                return
            self.new = False
        if self.theme.editable:
            await self.theme.save()
            await interaction.response.edit_message(content='Theme saved successfully!', view=None, embeds=[], delete_after=5)
        else:
            await interaction.response.edit_message(view=None, delete_after=5)
        self.stop()

    @ui.button(label='Share', style=discord.ButtonStyle.gray)
    async def share_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(embed=self.get_embed(), ephemeral=False)


# noinspection PyUnresolvedReferences
class RoleEditView(ui.View):
    def __init__(self, role: 'ThemeRole', *, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.role = role
        self.delete = False
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

    @ui.button(label='Delete', style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: ui.Button):
        self.delete = True
        await interaction.response.defer()
        self.stop()


# noinspection PyUnresolvedReferences
class GroupEditView(ui.View):
    def __init__(self, group: 'DynamicVoiceGroup', *, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.group = group
        self.delete = False
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
            title='Edit Channel Group',
            description=f'Template: **{self.group.template}**\n'
                        f'Minimum: {self.group.min}\n'
                        f'Maximum: {self.group.max}\n'
                        f'Minimum Empty: {self.group.min_empty}\n'
                        f'Game Template: {self.group.game_template}',
            color=discord.Color.blurple()
        )
        embed.set_footer(text='Use {n} for channel number, {st} for the 1(st) 2(nd) parts if desired, and {g} for game name in templates.')
        embeds.append(embed)
        return embeds

    @ui.button(label='Change Template', style=discord.ButtonStyle.primary)
    async def change_template_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Group Template', 'Template')
        modal = modal_cls(default=self.group.template)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        if not modal.value:
            self.error_message = 'Group template cannot be empty.'
        elif '{n}' not in modal.value:
            self.error_message = 'Group template must contain {n} for channel number.'
        else:
            self.group.template = modal.value
            self.error_message = None
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Change Game Template', style=discord.ButtonStyle.primary)
    async def change_game_template_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Group Game Template', 'Game Template')
        modal = modal_cls(default=self.group.game_template)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        if not modal.value:
            self.error_message = 'Group game template cannot be empty.'
        elif '{n}' not in modal.value or '{g}' not in modal.value:
            self.error_message = 'Group game template must contain {n} for channel number and {g} for game name.'
        else:
            self.group.game_template = modal.value
            self.error_message = None
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Change Minimum', style=discord.ButtonStyle.primary)
    async def change_minimum_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Group Minimum Channels', 'Minimum')
        modal = modal_cls(default=str(self.group.min))
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        try:
            minimum = int(modal.value)
            if minimum < 0:
                self.error_message = 'Minimum cannot be negative.'
            elif minimum > self.group.max:
                self.error_message = 'Minimum cannot be greater than maximum.'
            else:
                self.group.min = minimum
                self.error_message = None
        except ValueError:
            self.error_message = 'Invalid minimum value. Please enter a valid number.'
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Change Maximum', style=discord.ButtonStyle.primary)
    async def change_maximum_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Group Maximum Channels', 'Maximum')
        modal = modal_cls(default=str(self.group.max))
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        try:
            maximum = int(modal.value)
            if maximum <= 0:
                self.error_message = 'Maximum must be a positive number.'
            elif maximum < self.group.min:
                self.error_message = 'Maximum cannot be less than minimum.'
            else:
                self.group.max = maximum
                self.error_message = None
        except ValueError:
            self.error_message = 'Invalid maximum value. Please enter a valid number.'
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Change Minimum Empty', style=discord.ButtonStyle.primary)
    async def change_minimum_empty_button(self, interaction: discord.Interaction, button: ui.Button):
        modal_cls = get_simple_modal('Change Group Minimum Empty Channels', 'Minimum Empty')
        modal = modal_cls(default=str(self.group.min_empty))
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.interaction
        try:
            minimum_empty = int(modal.value)
            if minimum_empty < 0:
                self.error_message = 'Minimum empty cannot be negative.'
            elif minimum_empty > self.group.max:
                self.error_message = 'Minimum empty cannot be greater than maximum.'
            elif minimum_empty > self.group.min:
                self.error_message = 'Minimum empty cannot be greater than minimum.'
            else:
                self.group.min_empty = minimum_empty
                self.error_message = None
        except ValueError:
            self.error_message = 'Invalid minimum empty value. Please enter a valid number.'
        await interaction.edit_original_response(embeds=self.get_embeds(), view=self)

    @ui.button(label='Close', style=discord.ButtonStyle.gray)
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.stop()

    @ui.button(label='Delete', style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: ui.Button):
        self.delete = True
        await interaction.response.defer()
        self.stop()
