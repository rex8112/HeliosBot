import asyncio
from typing import TYPE_CHECKING, Dict

import discord

from .exceptions import IdMismatchError
from .channel_manager import ChannelManager

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from helios import ServerManager


class Server:
    def __init__(self, bot: 'HeliosBot', manager: 'ServerManager', guild: discord.Guild):
        self.loaded = False
        self.bot = bot
        self.guild = guild
        self.manager = manager
        self.channels = ChannelManager(self)
        self.private_voice_channels = {}
        self.topics = {}
        self.settings = {}
        self.flags = []

        self._event = asyncio.Event()

    # Properties
    @property
    def name(self):
        return self.guild.name

    @property
    def id(self):
        return self.guild.id

    # Methods
    def deserialize(self, data: Dict) -> None:
        """
        Takes a dictionary from the Helios API and fills out the class
        :param data: A JSON Dictionary from the Helios API
        :raises helios.IdMismatchError: When the ID in the data does not equal the ID in the given guild
        """
        if data.get('id') != self.id:
            raise IdMismatchError('ID in data does not match server ID', self.id, data.get('id'))
        self.settings = data.get('settings')
        self.flags = data.get('flags')
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
