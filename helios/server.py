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

import json
from typing import TYPE_CHECKING, Dict, Optional

import discord

from .channel_manager import ChannelManager
from .court import Court
from .database import ServerModel, objects
from .exceptions import IdMismatchError
from .member import HeliosMember
from .member_manager import MemberManager
from .shop import Shop
from .tools.new_setting import Settings, SettingItem
from .music import MusicPlayer

if TYPE_CHECKING:
    from .server_manager import ServerManager


class ServerSettings(Settings):
    archive_category = SettingItem('archive_category', None, discord.CategoryChannel)
    topic_category = SettingItem('topic_category', None, discord.CategoryChannel)
    voice_controller = SettingItem('voice_controller', None, discord.Role)
    verified_role = SettingItem('verified_role', None, discord.Role)
    partial = SettingItem('partial', 4, int)
    points_per_minute = SettingItem('points_per_minute', 1, int)
    private_create = SettingItem('private_create', None, discord.VoiceChannel)
    points_name = SettingItem('points_name', 'mins', str)


class Server:
    _default_settings = {
        'archive_category': None,
        'topic_category': None,
        'voice_controller': None,
        'verified_role': None,
        'partial': 4,
        'points_per_minute': 1,
        'private_create': None,
        'on_voice': {},
        'points_name': 'mins'
    }

    def __init__(self, manager: 'ServerManager', guild: discord.Guild):
        self.loaded = False
        self.bot = manager.bot
        self.guild = guild
        self.manager = manager
        self.channels = ChannelManager(self)
        self.members = MemberManager(self)
        self.shop = Shop(self.bot)
        self.court = Court(self)
        self.music_player = MusicPlayer(self)
        self.topics = {}
        self.voice_controllers = []
        self.settings = ServerSettings(self.bot)
        self.flags = []

        self._new = False
        self._save_task = None
        self.db_entry = None

    # Properties
    @property
    def name(self):
        return self.guild.name

    @property
    def id(self):
        return self.guild.id

    @property
    def db_id(self):
        return self.db_entry.id

    @property
    def private_create_channel(self) -> Optional[discord.VoiceChannel]:
        return self.settings.private_create.value

    @property
    def voice_controller_role(self) -> Optional[discord.Role]:
        roles = self.guild.roles
        for role in roles:
            if role.name == 'VoiceControlled':
                return role

    @property
    def verified_role(self) -> Optional[discord.Role]:
        role = self.settings.verified_role.value
        if role is None:
            self.settings.verified_role = None
        return role

    @property
    def points_name(self) -> str:
        return self.settings.points_name.value

    @property
    def me(self) -> 'HeliosMember':
        return self.members.get(self.bot.user.id)

    @classmethod
    def new(cls, manager: 'ServerManager', guild: discord.Guild):
        s = cls(manager, guild)
        s._new = True
        s.loaded = True
        return s

    # Methods
    def deserialize(self, data: ServerModel) -> None:
        """
        Takes a dictionary from the Helios API and fills out the class
        :param data: A JSON Dictionary from the Helios API
        :raises helios.IdMismatchError: When the ID in the data does not equal the ID in the given guild
        """
        if data.id != self.id:
            raise IdMismatchError('ID in data does not match server ID', self.id, data.id)
        self.flags = json.loads(data.flags)
        self.settings.load_dict(json.loads(data.settings))
        self.db_entry = data
        self.loaded = True

    def serialize(self) -> Dict:
        """
        Returns a JSON Serializable object.
        :return: A JSON Serializable object
        """
        data = {
            'id': self.id,
            'name': self.name,
            'settings': json.dumps(self.settings.to_dict()),
            'flags': json.dumps(self.flags)
        }

        return data

    async def add_on_voice(self, member: 'HeliosMember', action: str):
        return await self.bot.event_manager.add_action('on_voice', member, action)

    def queue_save(self):
        if self._save_task:
            return
        self._save_task = self.bot.loop.create_task(self.save())

    async def save(self):
        try:
            if self._new:
                self.db_entry = objects.create(ServerModel, **self.serialize())
                self._new = False
            else:
                self.db_entry.update_model_instance(self.db_entry, self.serialize())
                await objects.update(self.db_entry)
        finally:
            self._save_task = None

    async def do_on_voice(self, helios_member: 'HeliosMember'):
        if helios_member.allow_on_voice is False:
            return
        member: discord.Member = helios_member.member
        actions = await self.bot.event_manager.get_actions('on_voice', helios_member)
        edits = {}
        for action in actions:
            if action.action == 'unmute':
                edits['mute'] = False
            elif action.action == 'mute':
                edits['mute'] = True
            if action.action == 'undeafen':
                edits['deafen'] = False
            elif action.action == 'deafen':
                edits['deafen'] = True
        if len(edits) > 0:
            await member.edit(**edits)
            await self.bot.event_manager.clear_actions('on_voice', helios_member)
            await self.save()
