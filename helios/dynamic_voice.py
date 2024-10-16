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
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Optional, Union

import discord

from .database import DynamicVoiceGroupModel, DynamicVoiceModel
from .pug import PUGManager
from .tools.settings import Settings, SettingItem, StringSettingItem
from .views import DynamicVoiceView, PrivateVoiceView
from .voice_template import VoiceTemplate

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .member import HeliosMember
    from .server import Server


logger = logging.getLogger('HeliosLogger.DynamicVoice')


class DynamicVoiceState(Enum):
    ACTIVE = 0
    INACTIVE = 1
    PRIVATE = 2
    CONTROLLED = 3


class VoiceSettings(Settings):
    number = SettingItem('number', 0, int)
    group = SettingItem('group', None, int)
    state = SettingItem('state', 1, int)
    owner = SettingItem('owner', None, discord.Member)
    template = StringSettingItem('template', None)
    control_message = SettingItem('control_message', None, discord.PartialMessage)
    inactive = SettingItem('inactive', False, bool)
    custom_name = SettingItem('custom_name', None, str)


class DynamicVoiceChannel:
    NAME_COOLDOWN = timedelta(minutes=5)
    MESSAGE_UPDATE_COOLDOWN = timedelta(seconds=1)

    def __init__(self, manager: 'VoiceManager', channel: discord.VoiceChannel):
        """A dynamic voice channel."""
        self.manager = manager
        self.server = manager.server
        self.channel = channel
        self.settings = VoiceSettings(self.bot)

        self.prefix = ''
        self.majority_game = None

        self.free = True

        self.db_entry = None
        self._unsaved = False
        self._last_name_change = discord.utils.utcnow() - self.NAME_COOLDOWN
        self._last_message_update = discord.utils.utcnow() - self.MESSAGE_UPDATE_COOLDOWN
        self._private_on = datetime.now().astimezone()
        self._custom_view_type = None
        self._fetched_control_message = None
        self._should_update = False

        self._template = None

    def __enter__(self):
        self.free = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.free = True

    # Properties
    @property
    def bot(self) -> 'HeliosBot':
        return self.server.bot

    @property
    def id(self):
        return self.channel.id

    @property
    def number(self):
        return self.settings.number.value

    @number.setter
    def number(self, value):
        self.settings.number.value = value
        self._unsaved = True

    @property
    def group(self) -> Optional['DynamicVoiceGroup']:
        return self.manager.groups[self.settings.group.value] if self.settings.group.value is not None else None

    @group.setter
    def group(self, value: Optional['DynamicVoiceGroup']):
        self.settings.group.value = value.id if value else None
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
        return self.server.members.get(self.owner.id) if self.owner else None

    @h_owner.setter
    def h_owner(self, value: 'HeliosMember'):
        self.owner = value.member

    @property
    def state(self) -> DynamicVoiceState:
        return DynamicVoiceState(self.settings.state.value)

    @state.setter
    def state(self, value: DynamicVoiceState):
        self.settings.state.value = value.value
        self._unsaved = True

    @property
    def effects(self):
        return self.bot.effects.get_effects(self)

    @property
    def template(self):
        if self._template:
            return self._template
        temp = VoiceTemplate(self.h_owner, self.channel.name, data=json.loads(self.settings.template.value))
        if temp in self.h_owner.templates:
            temp = self.h_owner.templates[self.h_owner.templates.index(temp)]
        self._template = temp
        return temp

    @template.setter
    def template(self, value: Optional[VoiceTemplate]):
        if value is None:
            self.settings.template.value = None
        else:
            self.settings.template.value = json.dumps(value.serialize())
        self._template = value
        self._unsaved = True

    @property
    def _control_message(self) -> Optional[discord.PartialMessage]:
        return self.settings.control_message.value

    @_control_message.setter
    def _control_message(self, value: discord.Message):
        self._fetched_control_message = value
        partial = value.channel.get_partial_message(value.id)
        self.settings.control_message.value = partial
        self._unsaved = True

    @property
    def inactive(self) -> bool:
        return self.settings.inactive.value

    @inactive.setter
    def inactive(self, value: bool):
        self.settings.inactive.value = value
        self._unsaved = True

    @property
    def custom_name(self) -> Optional[str]:
        return self.settings.custom_name.value

    @custom_name.setter
    def custom_name(self, value: Optional[str]):
        self.settings.custom_name.value = value
        self._unsaved = True

    @property
    def inactive_overwrites(self):
        return {self.server.guild.default_role: discord.PermissionOverwrite(view_channel=False)}

    @property
    def alive(self):
        if self.channel is not None and self.bot.get_channel(self.id):
            return True
        else:
            return False

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
            d_channel = manager.server.guild.get_channel(entry.channel)
            if d_channel is None:
                await DynamicVoiceModel.async_delete(entry)
                continue
            channel = cls(manager, d_channel)
            channel.settings.load_dict(entry.settings)
            channel.db_entry = entry
            channels.append(channel)
        return channels

    # Database Methods
    async def save(self):
        if self.db_entry and self._unsaved:
            await DynamicVoiceModel.async_update(self.db_entry, **self.serialize())

    async def delete(self):
        await DynamicVoiceModel.async_delete(self.db_entry)
        del self.manager.channels[self.channel.id]
        try:
            await self.channel.delete()
        except discord.NotFound:
            ...

    # Methods
    async def get_control_message(self):
        if self._control_message:
            if self._fetched_control_message is None:
                try:
                    return await self._control_message.fetch()
                except discord.NotFound:
                    ...
            else:
                return self._fetched_control_message
        return None

    async def send_control_message(self):
        if self._control_message:
            try:
                await self._control_message.delete()
            except (discord.NotFound, discord.HTTPException):
                ...
        if self.state == DynamicVoiceState.PRIVATE:
            view = PrivateVoiceView(self)
        elif self.state == DynamicVoiceState.CONTROLLED:
            view = self._custom_view_type(self)
        else:
            view = DynamicVoiceView(self)
        message = await self.channel.send(embeds=await view.get_embeds(), view=view)
        self._control_message = message
        self._last_message_update = datetime.now().astimezone()
        await self.save()

    @staticmethod
    async def is_visible(message: discord.Message):
        last_few = [x async for x in message.channel.history(limit=5)]
        for i, m in enumerate(last_few):
            if m.id == message.id:
                return True
            elif m.embeds:
                return False # If there are any embeds in the last few messages, the message is probably not visible
        return False

    async def update_control_message(self, force=False):
        message = await self.get_control_message()
        if force or message is None or self._should_update or not await self.is_visible(message):
            if self.message_on_cooldown():
                self._should_update = True
                return
            self._should_update = False
            await self.send_control_message()

    async def get_majority_game(self):
        games = {None: 0}
        for member in self.channel.members:
            h_member = self.server.members.get(member.id)
            if member.bot:
                continue
            activity = h_member.get_game_activity()
            if activity is None:
                games[None] += 1
                continue
            activity = await self.server.games.get_game(activity.name)
            if activity.name not in games:
                games[activity.name] = 0
            games[activity.name] += 1
        game = max(games, key=games.get)
        if games[game] <= len(self.channel.members) / 2:
            self.majority_game = None
            return None
        self.majority_game = game
        return game

    def name_on_cooldown(self):
        return datetime.now().astimezone() - self._last_name_change < self.NAME_COOLDOWN

    def message_on_cooldown(self):
        return datetime.now().astimezone() - self._last_message_update < self.MESSAGE_UPDATE_COOLDOWN

    async def update_name(self):
        if self.state == DynamicVoiceState.INACTIVE:
            return
        if self.state == DynamicVoiceState.PRIVATE:
            new_name = self.template.name
        elif self.custom_name:
            new_name = self.custom_name
        else:
            game = await self.get_majority_game()
            if game:
                game = await self.server.games.get_game(game)
                new_name = self.group.get_game_name(self.number, game.display_name)
            else:
                new_name = self.group.get_name(self.number)
        new_name = self.prefix + new_name

        if new_name != self.channel.name and not self.name_on_cooldown():
            await self.channel.edit(name=new_name)
            await self.update_control_message(force=True)
            self._last_name_change = datetime.now().astimezone()

    def build_template(self, owner: 'HeliosMember') -> VoiceTemplate:
        template = VoiceTemplate(owner, self.channel.name)
        channel = self.channel
        # last_template = owner.templates[0] if owner.templates else None
        # use = True
        # if last_template:
        #     for member in channel.members:
        #         if member.id not in last_template.denied:
        #             use = False
        #             break
        #         elif last_template.private and member.id not in last_template.allowed:
        #             use = False
        #             break
        # else:
        #     last_template = owner.create_template()
        #     for member in channel.members:
        #         last_template.allow(member)
        # if use:
        #     return last_template
        for member in channel.members:
            template.allow(member)
        template.private = True
        return template

    async def apply_template(self, template: VoiceTemplate):
        await self.channel.edit(overwrites=template.overwrites, nsfw=template.nsfw)
        self.template = template

    def occupied(self):
        return len(self.channel.members) > 0

    def has_effect(self, effect: str):
        effects = self.effects
        for e in effects:
            if e.type.lower() == effect.lower():
                return True
        return False

    def remain_private(self):
        before = datetime.now().astimezone() - timedelta(minutes=5)
        if self.state != DynamicVoiceState.PRIVATE:
            return False
        if len(self.channel.members) > 0:
            return True
        elif self._private_on > before:
            return True
        else:
            return False

    async def make_private(self, owner: 'HeliosMember', template: Optional[VoiceTemplate] = None):
        """Make the channel private."""
        if self.state != DynamicVoiceState.PRIVATE:
            self.unmake_active()
            self.owner = owner.member
            self.state = DynamicVoiceState.PRIVATE
            if template is None:
                template = self.build_template(owner)
                await owner.save()
            self.template = template
            self._private_on = datetime.now().astimezone()
            await self.apply_template(template)
            await self.update_name()
            await self.update_control_message(force=True)
            await self.save()

    async def purge_channel(self):
        await self.channel.purge(limit=None, bulk=True)

    async def unmake_private(self):
        """Unmake the channel private."""
        if self.state == DynamicVoiceState.PRIVATE:
            await self.purge_channel()
            if self.channel.nsfw:
                await self.channel.edit(nsfw=False)
            self.template = None
            self.owner = None

    async def make_active(self, group: 'DynamicVoiceGroup'):
        """Make the channel active."""
        if self.state != DynamicVoiceState.ACTIVE:
            await self.unmake_private()
            self.unmake_controlled()
            self.state = DynamicVoiceState.ACTIVE
            self.number = self.manager.get_next_number(group)
            self.group = group
            await self.channel.edit(sync_permissions=True)
            await self.update_name()
            await self.update_control_message(force=True)
            await self.save()

    def unmake_active(self):
        """Unmake the channel active."""
        if self.state == DynamicVoiceState.ACTIVE:
            self.group = None
            self.number = 0

    async def make_controlled(self, custom_view_type: type):
        """Make the channel controlled."""
        if self.state != DynamicVoiceState.CONTROLLED:
            self.unmake_active()
            await self.unmake_private()
            self.state = DynamicVoiceState.CONTROLLED
            self._custom_view_type = custom_view_type
            await self.save()
        else:
            self._custom_view_type = custom_view_type

    def unmake_controlled(self):
        """Unmake the channel controlled."""
        if self.state == DynamicVoiceState.CONTROLLED:
            self._custom_view_type = None
            self.custom_name = None

    async def make_inactive(self, force=False):
        """Make the channel inactive."""
        if self.state != DynamicVoiceState.INACTIVE or force:
            self.unmake_active()
            self.unmake_controlled()
            await self.unmake_private()
            self.state = DynamicVoiceState.INACTIVE

            for effect in self.bot.effects.get_effects(self):
                await self.bot.effects.remove_effect(effect)

            await self.channel.edit(
                overwrites=self.inactive_overwrites
            )
            self.custom_name = None
            await self.save()


class DynamicVoiceGroupSettings(Settings):
    min = SettingItem('min', 1, int)
    min_empty = SettingItem('min_empty', 1, int)
    max = SettingItem('max', 0, int)
    template = StringSettingItem('template', 'Channel {n}', min_length=3, max_length=25)
    game_template = StringSettingItem('game_template', 'Channel {n} - {g}', min_length=3, max_length=22)


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
        self.settings = DynamicVoiceGroupSettings(self.server.bot)
        self.settings.min.value = minimum
        self.settings.min_empty.value = minimum_empty
        self.settings.max.value = maximum
        self.settings.template.value = template
        self.settings.game_template.value = game_template

        self.db_entry = None

    # Properties
    @property
    def id(self):
        return self.db_entry.id if self.db_entry else None

    @property
    def min(self):
        return self.settings.min.value

    @min.setter
    def min(self, value):
        self.settings.min.value = value

    @property
    def min_empty(self):
        return self.settings.min_empty.value

    @min_empty.setter
    def min_empty(self, value):
        self.settings.min_empty.value = value

    @property
    def max(self):
        return self.settings.max.value

    @max.setter
    def max(self, value):
        self.settings.max.value = value

    @property
    def template(self):
        return self.settings.template.value

    @template.setter
    def template(self, value):
        self.settings.template.value = value

    @property
    def game_template(self):
        return self.settings.game_template.value

    @game_template.setter
    def game_template(self, value):
        self.settings.game_template.value = value

    # Methods
    def get_name(self, number: int):
        return self.template.replace('{n}', str(number))

    def get_game_name(self, number: int, game: str):
        template = self.game_template
        template.replace('{g}', '')
        length = len(template)
        if length + len(game) > 25:
            game = game[:25 - length - 3] + '...'

        return self.game_template.replace('{n}', str(number)).replace('{g}', game)

    def serialize(self) -> dict:
        return {
            'min': self.min,
            'min_empty': self.min_empty,
            'max': self.max,
            'template': self.template,
            'game_template': self.game_template
        }

    @classmethod
    async def create(cls, server: 'Server', minimum: int, minimum_empty: int, template: str, game_template: str, maximum: int = 0):
        group = cls(server, minimum, minimum_empty, template, game_template, maximum)
        group.db_entry = await DynamicVoiceGroupModel.create_model(server.db_entry, **group.serialize())
        return group

    @classmethod
    async def get_all(cls, server: 'Server') -> list['DynamicVoiceGroup']:
        groups = []
        db_groups = await DynamicVoiceGroupModel.get_all(server.db_entry)

        for entry in db_groups:
            group = cls(server, entry.min, entry.min_empty, entry.template, entry.game_template, entry.max)
            group.db_entry = entry
            groups.append(group)
        return groups

    async def save(self):
        if self.db_entry:
            await DynamicVoiceGroupModel.async_update(self.db_entry, **self.serialize())


def need_sorting(all_channels):
    discord_channels = all_channels[0].channel.category.voice_channels
    for i, channel in enumerate(all_channels):
        if channel.channel != discord_channels[i]:
            return True
    return False


class VoiceManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.channels: dict[int, DynamicVoiceChannel] = {}
        self.groups: dict[int, DynamicVoiceGroup] = {}
        self.pug_manager: 'PUGManager' = PUGManager(self.server)

        self._setup = False

    @property
    def inactive_overwrites(self):
        return {self.server.guild.default_role: discord.PermissionOverwrite(view_channel=False)}

    async def setup(self):
        groups = await DynamicVoiceGroup.get_all(self.server)
        for group in groups:
            self.groups[group.id] = group

        channels = await DynamicVoiceChannel.get_all(self)
        for channel in channels:
            self.channels[channel.channel.id] = channel
        await self.pug_manager.load_pugs()
        self._setup = True

    async def sort_channels(self):
        all_channels = []
        grouped = []
        for group in self.groups.values():
            channels = sorted(self.get_active(group), key=lambda x: x.number)
            grouped.append(channels)
            all_channels += channels

        for channel in all_channels:  # Make sure all channels are in the correct category
            category = self.server.settings.dynamic_voice_category.value
            if channel.channel.category != self.server.guild.get_channel(
                    self.server.settings.dynamic_voice_category.value.id):
                logger.warning(f'{channel.channel.name} was not in the correct category. Moving it.')
                await channel.channel.edit(category=category)

        if need_sorting(all_channels):
            for i, channel in enumerate(all_channels):
                await channel.channel.edit(position=i)

        for channels in grouped:
            for i, channel in enumerate(channels):
                if channel.number != i + 1 and not channel.channel.members:
                    channel.number = i + 1
                    await channel.save()

    async def update_names(self):
        for channel in self.channels.values():
            try:
                await channel.update_name()
            except AttributeError:
                ...

    async def update_control_messages(self):
        for channel in self.channels.values():
            if channel.state != DynamicVoiceState.INACTIVE:
                await channel.update_control_message()

    async def check_channels(self):
        if not self._setup:
            return

        all_max = 0
        logger.debug(f'{self.server.name}: Voice Manager: Checking Groups')
        for group in self.groups.values():
            all_max += group.max
            active = self.get_active(group)
            empty = sorted(self.get_empty(group), key=lambda x: x.number, reverse=True)
            channels_to_change = 0
            if len(active) < group.min:  # If there are not enough active channels to meet the minimum
                channels_to_change = group.min - len(active)
            elif len(empty) < group.min_empty:  # If there are not enough empty channels to meet the empty minimum
                channels_to_change = group.min_empty - len(empty)
            elif len(empty) > group.min_empty:  # If there are too many empty channels
                channels_to_change = group.min_empty - len(empty)

            channels_to_change = min(channels_to_change, group.max - len(active))  # Keep at most the maximum
            channels_to_change = max(channels_to_change, group.min - len(active))  # Keep at least the minimum
            logger.debug(f'{self.server.name}: Voice Manager: {group.template} - {channels_to_change} channels to change')

            if channels_to_change > 0:
                for _ in range(channels_to_change):
                    channel = await self.get_inactive_channel()
                    await channel.make_active(group)
            elif channels_to_change < 0:
                for i, empty in enumerate(empty):
                    if i < abs(channels_to_change):
                        await empty.make_inactive()
                    else:
                        break

        private = self.get_private()
        for channel in private:
            if not channel.remain_private():
                await channel.make_inactive()

        # Check if the group has too many channels and remove inactive channels to try and meet that
        inactive = self.get_inactive()
        if 0 < all_max < len(inactive):
            to_delete = len(inactive) - all_max
            for i in range(to_delete):
                try:
                    await inactive.pop().delete()
                except IndexError:
                    break

        try:
            logger.debug(f'{self.server.name}: Voice Manager: Updating Control Messages')
            await self.update_control_messages()
            logger.debug(f'{self.server.name}: Voice Manager: Sorting Channels')
            await self.sort_channels()
            logger.debug(f'{self.server.name}: Voice Manager: Updating Names')
            await self.update_names()
            logger.debug(f'{self.server.name}: Voice Manager: Managing PUGs')
            await self.pug_manager.manage_pugs()
            logger.debug(f'{self.server.name}: Voice Manager: Done')
        except Exception as e:
            logger.error(e, exc_info=True)

    async def get_inactive_channel(self):
        inactive = self.get_inactive()
        ready_inactive = list(filter(lambda x: x.name_on_cooldown() is False and x.free is True, inactive))

        if len(ready_inactive) > 0:
            return ready_inactive.pop()
        else:
            return await self.create_channel()

    async def create_channel(self):
        channel = await self.server.guild.create_voice_channel(
            name='Inactive Channel',
            category=self.server.settings.dynamic_voice_category.value,
            overwrites=self.inactive_overwrites
        )
        channel = await DynamicVoiceChannel.create(self, channel)
        await channel.save()
        self.channels[channel.channel.id] = channel
        return channel

    async def reset_channel(self, channel: Union[discord.VoiceChannel, DynamicVoiceChannel]):
        if isinstance(channel, discord.VoiceChannel):
            channel = self.channels[channel.id]

        await channel.purge_channel()
        channel.settings = VoiceSettings(self.server.bot)
        await channel.make_inactive(force=True)


    async def create_group(self, minimum: int, minimum_empty: int, template: str, game_template: str, maximum: int = 0):
        group = await DynamicVoiceGroup.create(self.server, minimum, minimum_empty, template, game_template, maximum)
        self.groups[group.id] = group
        await self.check_channels()
        return group

    async def delete_group(self, group: 'DynamicVoiceGroup'):
        for channel in self.get_group_channels(group):
            await channel.delete()
        await DynamicVoiceGroupModel.async_delete(group.db_entry)
        del self.groups[group.id]

    def get_next_number(self, group: 'DynamicVoiceGroup'):
        channels = sorted(self.get_group_channels(group), key=lambda x: x.number)
        for i, channel in enumerate(channels, start=1):
            if channel.number != i:
                return i
        return len(channels) + 1

    def get_group_channels(self, group: 'DynamicVoiceGroup') -> list[DynamicVoiceChannel]:
        try:
            return list(filter(lambda x: x.group == group, self.channels.values()))
        except Exception as e:
            logger.error(e, exc_info=True)
            return []

    def get_active(self, group: 'DynamicVoiceGroup' = None) -> list[DynamicVoiceChannel]:
        if group:
            return list(filter(lambda x: x.state == DynamicVoiceState.ACTIVE and x.group == group, self.channels.values()))
        else:
            return list(filter(lambda x: x.state == DynamicVoiceState.ACTIVE, self.channels.values()))

    def get_inactive(self, group: 'DynamicVoiceGroup' = None) -> list[DynamicVoiceChannel]:
        if group:
            return list(filter(lambda x: x.state == DynamicVoiceState.INACTIVE and x.group == group,
                               self.channels.values()))
        else:
            return list(filter(lambda x: x.state == DynamicVoiceState.INACTIVE, self.channels.values()))

    def get_private(self, group: 'DynamicVoiceGroup' = None) -> list[DynamicVoiceChannel]:
        if group:
            return list(filter(lambda x: x.state == DynamicVoiceState.PRIVATE and x.group == group,
                               self.channels.values()))
        else:
            return list(filter(lambda x: x.state == DynamicVoiceState.PRIVATE, self.channels.values()))

    def get_empty(self, group: 'DynamicVoiceGroup' = None) -> list[DynamicVoiceChannel]:
        if group:
            active = self.get_active(group)
        else:
            active = self.get_active()
        return list(filter(lambda x: x.occupied() is False, active))
