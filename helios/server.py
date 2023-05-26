from typing import TYPE_CHECKING, Dict, Optional

import discord

from .channel_manager import ChannelManager
from .exceptions import IdMismatchError
from .member_manager import MemberManager
from .stadium import Stadium
from .tools.settings import Settings
from .database import ServerModel, update_model_instance

if TYPE_CHECKING:
    from .server_manager import ServerManager


class Server:
    _default_settings = {
        'archive_category': None,
        'topic_category': None,
        'voice_controller': None,
        'partial': 4,
        'points_per_minute': 1,
        'private_create': None
    }

    def __init__(self, manager: 'ServerManager', guild: discord.Guild):
        self.loaded = False
        self.bot = manager.bot
        self.guild = guild
        self.manager = manager
        self.channels = ChannelManager(self)
        self.members = MemberManager(self)
        self.stadium = Stadium(self)
        self.topics = {}
        self.voice_controllers = []
        self.settings = Settings(self._default_settings, bot=self.bot, guild=self.guild)
        self.flags = []

        self._new = False
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

    @classmethod
    def new(cls, manager: 'ServerManager', guild: discord.Guild):
        s = cls(manager, guild)
        s._new = True
        s.loaded = True
        return s

    # Methods
    def deserialize(self, data: Dict) -> None:
        """
        Takes a dictionary from the Helios API and fills out the class
        :param data: A JSON Dictionary from the Helios API
        :raises helios.IdMismatchError: When the ID in the data does not equal the ID in the given guild
        """
        if data.get('id') != self.id:
            raise IdMismatchError('ID in data does not match server ID', self.id, data.get('id'))
        self.flags = data.get('flags')
        settings = {**self._default_settings, **data.get('settings', {})}
        self.settings = Settings(settings, bot=self.bot, guild=self.guild)
        self.loaded = True

    def serialize(self) -> Dict:
        """
        Returns a JSON Serializable object.
        :return: A JSON Serializable object
        """
        data = {
            'id': self.id,
            'name': self.name,
            'settings': self.settings.to_dict(),
            'flags': self.flags
        }

        return data

    async def save(self):
        if self._new:
            self.db_entry = ServerModel(**self.serialize())
            self._new = False
        else:
            update_model_instance(self.db_entry, self.serialize())
        self.db_entry.save()
