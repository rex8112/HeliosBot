from typing import TYPE_CHECKING, Dict

import discord

from .channel_manager import ChannelManager
from .exceptions import IdMismatchError

if TYPE_CHECKING:
    from .server_manager import ServerManager


class Server:
    _default_settings = {
        'archive_category': None,
        'topic_category': None
    }

    def __init__(self, manager: 'ServerManager', guild: discord.Guild):
        self.loaded = False
        self.bot = manager.bot
        self.guild = guild
        self.manager = manager
        self.channels = ChannelManager(self)
        self.private_voice_channels = {}
        self.topics = {}
        self.settings = self._default_settings.copy()
        self.flags = []

        self._new = False

    # Properties
    @property
    def name(self):
        return self.guild.name

    @property
    def id(self):
        return self.guild.id

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
        settings = data.get('settings', {})
        for k, v in settings.items():
            self.settings[k] = v
        self.loaded = True

    def serialize(self) -> Dict:
        """
        Returns a JSON Serializable object.
        :return: A JSON Serializable object
        """
        data = {
            'id': self.id,
            'name': self.name,
            'settings': self.settings,
            'flags': self.flags
        }

        return data

    async def save(self):
        if self._new:
            await self.bot.helios_http.post_server(self.serialize())
            self._new = False
        else:
            await self.bot.helios_http.patch_server(self.serialize())
