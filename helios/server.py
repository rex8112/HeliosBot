import json
from typing import TYPE_CHECKING, Dict, Optional

import discord

from .channel_manager import ChannelManager
from .exceptions import IdMismatchError
from .event_manager import EventManager
from .member_manager import MemberManager
from .member import HeliosMember
from .shop import Shop
from .stadium import Stadium
from .tools.settings import Settings
from .database import ServerModel, update_model_instance, objects, EventModel

if TYPE_CHECKING:
    from .server_manager import ServerManager


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
        self.stadium = Stadium(self)
        self.shop = Shop(self.bot)
        self.topics = {}
        self.voice_controllers = []
        self.settings = Settings(self._default_settings, bot=self.bot, guild=self.guild)
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
    def private_create_channel(self) -> Optional[discord.VoiceChannel]:
        return self.settings.private_create

    @property
    def voice_controller_role(self) -> Optional[discord.Role]:
        roles = self.guild.roles
        for role in roles:
            if role.name == 'VoiceControlled':
                return role

    @property
    def verified_role(self) -> Optional[discord.Role]:
        role_id = self.settings.verified_role
        if role_id is None:
            return None
        role = self.guild.get_role(role_id)
        if role is None:
            self.settings.verified_role = None
        return role

    @property
    def points_name(self) -> str:
        return self.settings.points_name

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
        settings = {**self._default_settings, **json.loads(data.settings)}
        self.settings = Settings(settings, bot=self.bot, guild=self.guild)
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
                update_model_instance(self.db_entry, self.serialize())
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
