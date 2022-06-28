import discord
from discord.ext import commands
from typing import TYPE_CHECKING, Optional, Union


if TYPE_CHECKING:
    from discord.abc import PrivateChannel
    from helios import ChannelManager, HeliosBot, IdMismatchError
    from discord.types.threads import Thread
    from discord.types.channel import GuildChannel


class Channel:
    channel_type = 'Basic'

    def __init__(self,
                 bot: 'HeliosBot',
                 manager: 'ChannelManager',
                 *,
                 channel_id: int = None,
                 channel: Optional[Union['GuildChannel', 'Thread', 'PrivateChannel']] = None):
        """
        A special channel class that will hold all the important functions of that class
        :param bot: The bot being run
        :param manager: The channel manager handling this channel
        :param channel_id: The id of a discord channel, this will be fetched later
        :param channel: The discord channel of this channel
        """
        self.bot = bot
        self.manager = manager
        self.channel = None
        self.settings = {}
        self.flags = []
        self._id = None

        if channel:
            self.channel = channel
            self._id = channel.id
        elif channel_id:
            self._id = channel_id
        else:
            raise ValueError('_id or channel required.')

        self.loaded = False

    @property
    def id(self):
        if self.channel:
            return self.channel.id
        else:
            return self._id

    @property
    def server(self):
        return self.manager.server

    async def deserialize(self, data: dict) -> None:
        data_id = data.get('id')
        if data_id != self.id:
            raise IdMismatchError('ID of data does not match channel ID')

        self.settings = data.get('settings')
        self.flags = data.get('flags')
        self.loaded = True

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'server': self.server.id,
            'type': self.channel_type,
            'settings': self.settings,
            'flags': self.flags
        }
