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
from types import MethodType
from typing import TypeVar, Generic, Optional, Generator, Any

import discord.ext.commands

from ..views.generic_views import PaginatorSelectView

V = TypeVar('V')

defaults = dict[str, tuple[type[V], V]]


class Settings:
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    def __getitem__(self, item):
        value: 'SettingItem' = self._getitem_as_setting(item)
        if value is None:
            return None
        return value.value

    def _getitem_as_setting(self, item) -> Optional['SettingItem']:
        if isinstance(item, str):
            try:
                return getattr(self, item)
            except AttributeError:
                return None
        return None

    def __setitem__(self, key, value):
        item = self._getitem_as_setting(key)
        if isinstance(item, SettingItem):
            if type(value) is not item.type and value is not None:
                raise ValueError(f'Value must be of {item.type} type or None')
            item.value = value
        else:
            raise IndexError(f'{key} does not exsit')

    def all_settings(self) -> Generator['SettingItem', None, None]:
        for key in dir(self):
            if key.startswith('__'):
                continue
            value = getattr(self, key)
            if isinstance(value, SettingItem):
                yield value

    def to_dict(self) -> dict[str, Any]:
        d = {}
        for setting in self.all_settings():
            d[setting.key] = self.serialize_item(setting)
        return d

    def load_dict(self, data: dict) -> None:
        for key, value in data.items():
            try:
                setting: 'SettingItem' = getattr(self, key)
                self[key] = self.deserialize_item(setting.type, value)
            except AttributeError:
                ...

    def get_selection_view(self) -> PaginatorSelectView['SettingItem']:
        def get_embeds(values: list[SettingItem]):
            settings_string = ''
            for s in values:
                settings_string += f'**{s.title()} - {s.type.__name__}**\nCurrent: {s.value}\n\n'
            embed = discord.Embed(
                title='Settings',
                description=settings_string
            )
            return [embed]
        settings = [x for x in self.all_settings()]
        titles = [x.title() for x in settings]
        view = PaginatorSelectView(settings, titles, get_embeds)
        return view

    def get_item_view(self, setting: 'SettingItem'):
        view = SettingItemView(setting)
        return view

    # noinspection PyMethodMayBeStatic
    def serialize_item(self, item: 'SettingItem'):
        if item.value is None:
            return None
        if item.type in (int, str, float, bool):
            return item.value
        elif item.type in (discord.CategoryChannel, discord.VoiceChannel, discord.TextChannel, discord.Role):
            return item.value.id

    def deserialize_item(self, v_type: type, value: Any):
        if value is None:
            return None
        if v_type is int:
            return int(value)
        elif v_type is str:
            return str(value)
        elif v_type is float:
            return float(value)
        elif v_type is bool:
            return bool(value)
        elif v_type is discord.Role:
            return self.get_role(int(value))
        elif v_type in (discord.CategoryChannel, discord.VoiceChannel, discord.TextChannel):
            return self.bot.get_channel(int(value))

    def get_role(self, role_id: int) -> Optional[discord.Role]:
        for guild in self.bot.guilds:
            role = guild.get_role(role_id)
            if role:
                return role
        return None

    async def run(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(content='Building Settings')
        while True:
            view = self.get_selection_view()
            embeds = view.get_embeds(view.get_paged_values())
            await interaction.edit_original_response(content=None, view=view, embeds=embeds)
            if await view.wait():
                return
            i = view.last_interaction
            setting = view.selected
            view = setting.get_view()
            await i.edit_original_response(embed=setting.get_embed(), view=view)
            if await view.wait():
                return
            setting.value = view.value


class SettingItem(Generic[V]):
    def __init__(self, key: str, default_value: Optional[V], v_type: type[V], *, nullable=False):
        self.key: str = key
        self.value: Optional[V] = default_value
        self.type: type[V] = v_type
        self.nullable: bool = nullable

    def __repr__(self):
        return f'SettingItem<{self.type.__name__}, {self.value}>'

    def __eq__(self, other):
        if isinstance(other, SettingItem):
            return self.key == other.key and self.value == other.value
        return NotImplemented

    def __hash__(self):
        return hash(f'{self.type.__name__}.{self.key}.{self.value}')

    def title(self):
        return self.key.replace('_', ' ').title()

    def to_dict(self) -> dict[str, V]:
        return {self.key: self.value}

    def get_view(self):
        view = SettingItemView(self)
        return view

    def get_embed(self):
        return discord.Embed(
            title=self.title(),
            description=f'{self.type.__name__}\n\nCurrent Value: {self.value}',
            colour=discord.Colour.green()
        )


class SettingItemView(discord.ui.View):
    def __init__(self, setting: 'SettingItem'):
        super().__init__()
        self.timed_out = False
        self.value = None
        self.setting = setting
        self.build_view()

    def get_ui_item(self):
        if self.setting.type in (int, str, float):
            return PrimalModal(f'Enter {self.setting.type} value', self.setting.type)
        elif self.setting.type is bool:
            return BoolSelect()
        elif self.setting.type in (discord.CategoryChannel, discord.VoiceChannel, discord.TextChannel):
            if self.setting.type is discord.CategoryChannel:
                c_type = discord.ChannelType.category
            elif self.setting.type is discord.VoiceChannel:
                c_type = discord.ChannelType.voice
            elif self.setting.type is discord.TextChannel:
                c_type = discord.ChannelType.text
            else:
                c_type = discord.ChannelType.text
            return discord.ui.ChannelSelect(channel_types=[c_type])
        elif self.setting.type is discord.Role:
            return discord.ui.RoleSelect()

    def build_view(self):
        item = self.get_ui_item()
        if isinstance(item, PrimalModal):
            async def show_modal(s: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_modal(modal)
                if await modal.wait():
                    return
                self.value = modal.value
                self.stop()

            modal = item
            item = discord.ui.Button(label='Enter Value', style=discord.ButtonStyle.green)
            item.callback = MethodType(show_modal, item)
        elif isinstance(item, (discord.ui.Select,
                               discord.ui.ChannelSelect,
                               discord.ui.RoleSelect,
                               discord.ui.UserSelect)) and type(item) is not BoolSelect:
            async def set_value(s: discord.ui.Select, interaction: discord.Interaction):
                if len(s.values) == 1:
                    self.value = s.values[0]
                else:
                    self.value = [x for x in s.values]
                await interaction.response.defer()
                self.stop()
            item.callback = MethodType(set_value, item)
        self.add_item(item)

    async def on_timeout(self):
        self.timed_out = True


class BoolSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder='True or False',
            options=[
                discord.SelectOption(label='True'),
                discord.SelectOption(label='False')
            ]
        )
        self.value = None

    async def callback(self, interaction: discord.Interaction, /):
        option = self.values[0]
        if option == 'True':
            self.value = True
        else:
            self.value = False
        await interaction.response.send_message(content='Value Submitted', ephemeral=True)


class PrimalModal(discord.ui.Modal):
    value_text = discord.ui.TextInput(label='Value')

    def __init__(self, title: str, v_type: type, /):
        super().__init__(title=title)
        self.type = v_type
        self.value = None

    async def on_submit(self, interaction: discord.Interaction, /):
        value = self.value_text.value
        try:
            self.value = self.type(value)
        except ValueError:
            self.value = None
            await interaction.response.send_message(content=f'Invalid type, must be {self.type}', ephemeral=True)
            return
        await interaction.response.send_message(content='Submitted', ephemeral=True)
