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

import discord

from .database import DynamicVoiceGroupModel, DynamicVoiceModel
from .tools.settings import Settings, SettingItem
from .voice_template import VoiceTemplate

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .member import HeliosMember
    from .server import Server


class VoiceSettings(Settings):
    number = SettingItem('number', 1, int)
    group = SettingItem('group', None, int)
    private = SettingItem('private', False, bool)
    owner = SettingItem('owner', None, discord.Member)


class DynamicVoiceChannel:
    def __init__(self, manager: 'VoiceManager', channel: discord.VoiceChannel):
        """A dynamic voice channel."""
        self.manager = manager
        self.server = manager.server
        self.channel = channel
        self.settings = VoiceSettings(self.bot)

        self.custom_name = None

        self.db_entry = None
        self._unsaved = False

    # Properties
    @property
    def bot(self) -> 'HeliosBot':
        return self.server.bot

    @property
    def number(self):
        return self.settings.number.value

    @number.setter
    def number(self, value):
        self.settings.number.value = value
        self._unsaved = True

    @property
    def group(self) -> 'DynamicVoiceGroup':
        return self.manager.groups[self.settings.group.value]

    @group.setter
    def group(self, value: 'DynamicVoiceGroup'):
        self.settings.group.value = value.id
        self._unsaved = True

    @property
    def owner(self) -> discord.Member:
        return self.settings.owner.value

    @owner.setter
    def owner(self, value: discord.Member):
        self.settings.owner.value = value
        self._unsaved = True

    @property
    def h_owner(self) -> 'HeliosMember':
        return self.server.members.get(self.owner.id)

    @h_owner.setter
    def h_owner(self, value: 'HeliosMember'):
        self.owner = value.member

    @property
    def private(self) -> bool:
        return self.settings.private.value

    @private.setter
    def private(self, value: bool):
        self.settings.private.value = value
        self._unsaved = True

    def serialize(self) -> dict:
        return {
            'channel': self.channel.id,
            'settings': self.settings.to_dict()
        }

    # Class Methods
    @classmethod
    async def create(cls, manager: 'VoiceManager', channel: discord.VoiceChannel):
        vc = cls(manager, channel)
        vc.db_entry = await DynamicVoiceModel.create_model(manager.server.db_entry, **vc.serialize())
        return vc

    @classmethod
    async def get_all(cls, manager: 'VoiceManager') -> list['DynamicVoiceChannel']:
        channels = []
        db_channels = await DynamicVoiceModel.get_all(manager.server.db_entry)

        for entry in db_channels:
            channel = cls(manager, manager.server.guild.get_channel(entry.channel))
            channel.db_entry = entry
            channels.append(channel)
        return channels

    # Database Methods
    async def save(self):
        if self.db_entry and self._unsaved:
            await DynamicVoiceModel.async_update(self.db_entry, **self.serialize())

    async def delete(self):
        await DynamicVoiceModel.async_delete(self.db_entry)
        await self.channel.delete()

    # Methods
    def get_majority_game(self):
        games = {None: 0}
        for member in self.channel.members:
            if member.activity is None:
                games[None] += 1
                continue
            if member.activity.name not in games:
                games[member.activity.name] = 0
            games[member.activity.name] += 1
        return max(games, key=lambda x: games[x])

    async def update_name(self):
        if self.custom_name:
            await self.channel.edit(name=self.custom_name)
        else:
            game = self.get_majority_game()
            if game:
                await self.channel.edit(name=f'{game} {self.group.get_name(self.channel.position)}')
            else:
                await self.channel.edit(name=self.group.get_name(self.channel.position))

    def build_template(self) -> VoiceTemplate:
        template = VoiceTemplate(self.h_owner, self.channel.name)
        for member, perms in self.channel.overwrites.items():
            if isinstance(member, discord.Member):
                if perms.connect:
                    template.allow(member)
                else:
                    template.deny(member)
        return template

    async def apply_template(self, template: VoiceTemplate):
        await self.channel.edit(overwrites=template.overwrites)
        self.custom_name = template.name

    def occupied(self):
        return len(self.channel.members) > 0


class DynamicVoiceGroup:
    def __init__(self, server: 'Server', minimum: int, minimum_empty: int, template: str, game_template: str, maximum: int = 0):
        """"
        :param server: The server this group belongs to.
        :param minimum: The minimum number of members required to create a new channel.
        :param minimum_empty: The minimum number of empty channels.
        :param template: The template for the name of the channels. Use {n} for the number.
        :param game_template: The template for the name of the channels when a game is detected. Use {n} for the number and {g} for the game.
        :param maximum: The maximum number of channels allowed to be created.
        """
        self.server = server
        self.min = minimum
        self.min_empty = minimum_empty
        self.max = maximum
        self.template = template
        self.game_template = game_template

        self.db_entry = None

    @property
    def id(self):
        return self.db_entry.id if self.db_entry else None

    def get_name(self, number: int):
        return self.template.replace('{n}', str(number))

    def get_game_name(self, number: int, game: str):
        return self.game_template.replace('{n}', str(number)).replace('{g}', game)

    def serialize(self) -> dict:
        return {
            'min': self.min,
            'min_empty': self.min_empty,
            'max': self.max,
            'template': self.template
        }

    @classmethod
    async def create(cls, server: 'Server', minimum: int, minimum_empty: int, template: str, maximum: int = 0):
        group = cls(server, minimum, minimum_empty, template, maximum)
        group.db_entry = await DynamicVoiceGroupModel.create_model(server.db_entry, **group.serialize())
        return group

    @classmethod
    async def get_all(cls, server: 'Server') -> list['DynamicVoiceGroup']:
        groups = []
        db_groups = await DynamicVoiceGroupModel.get_all(server.db_entry)

        for entry in db_groups:
            group = cls(server, entry.min, entry.min_empty, entry.template, entry.max)
            group.db_entry = entry
            groups.append(group)
        return groups

    async def save(self):
        if self.db_entry:
            await DynamicVoiceGroupModel.async_update(self.db_entry, **self.serialize())


class VoiceManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.channels: dict[int, DynamicVoiceChannel] = {}
        self.groups: dict[int, DynamicVoiceGroup] = {}

    async def setup(self):
        groups = await DynamicVoiceGroup.get_all(self.server)
        for group in groups:
            self.groups[group.id] = group

        channels = await DynamicVoiceChannel.get_all(self)
        for channel in channels:
            self.channels[channel.channel.id] = channel

    async def sort_channels(self):
        channels = sorted(self.channels.values(), key=lambda x: x.channel.number)
        for i, channel in enumerate(channels):
            await channel.channel.edit(position=i)

    async def update_names(self):
        for channel in self.channels.values():
            await channel.update_name()

    async def check_channels(self):
        for group in self.groups.values():
            channels = self.get_group_channels(group)
            empty = self.get_empty(group)
            channels_to_change = 0
            if len(channels) < group.min:
                channels_to_change = group.min - len(channels)
            elif len(empty) < group.min_empty:
                channels_to_change = group.min_empty - len(empty)
            elif len(empty) > group.min_empty:
                channels_to_change = group.min_empty - len(empty)

            channels_to_change = min(channels_to_change, group.max - len(channels))

            if channels_to_change > 0:
                for _ in range(channels_to_change):
                    await self.create_channel(group)
            elif channels_to_change < 0:
                for i, empty in enumerate(empty):
                    if i < abs(channels_to_change):
                        await empty.delete()

        await self.sort_channels()
        await self.update_names()

    async def create_channel(self, group: 'DynamicVoiceGroup'):
        channel = await self.server.guild.create_voice_channel(
            name=group.get_name(self.get_next_number(group)),
            category=self.server.guild.get_channel(self.server.settings.dynamic_voice_category.value)
        )
        channel = await DynamicVoiceChannel.create(self, channel, group)
        self.channels[channel.channel.id] = channel
        return channel

    def get_next_number(self, group: 'DynamicVoiceGroup'):
        channels = sorted(self.get_group_channels(group), key=lambda x: x.number)
        for i, channel in enumerate(channels, start=1):
            if channel.number != i:
                return i
        return len(channels) + 1

    def get_group_channels(self, group: 'DynamicVoiceGroup'):
        return list(filter(lambda x: x.group == group, self.channels.values()))

    def get_empty(self, group: 'DynamicVoiceGroup' = None):
        if group:
            return list(filter(lambda x: x.occupied() is False and x.group == group, self.channels.values()))
        else:
            return list(filter(lambda x: x.occupied() is False, self.channels.values()))
