import datetime
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from helios import ChannelManager, HeliosBot


class Channel:
    channel_type = 'basic'
    _default_settings = {}
    _allowed_flags = []

    def __init__(self,
                 manager: 'ChannelManager',
                 data: dict):
        """
        A special channel class that will hold all the important functions of that class
        :param manager: The channel manager handling this channel
        :param data: Channel data dict
        """
        self.bot: 'HeliosBot' = manager.bot
        self.manager = manager
        self.channel = None
        self.settings = self._default_settings.copy()
        self.flags = []
        self._id = None

        self._id = data['id']
        self.channel = self.bot.get_channel(self._id)

        self._deserialize(data)

    @property
    def id(self):
        if self.channel:
            return self.channel.id
        else:
            return self._id

    @property
    def server(self):
        return self.manager.server

    @property
    def alive(self):
        if self.bot.get_channel(self.id):
            return True
        else:
            return False

    @classmethod
    def new(cls, manager: 'ChannelManager', channel_id: int):
        data = {
            'id': channel_id,
            'type': cls.channel_type,
        }
        return cls(manager, data)

    def set_flag(self, flag: str, on: bool):
        if flag not in self._allowed_flags:
            raise KeyError(f'{flag} not in {type(self)} allowed flags: {self._allowed_flags}')
        if flag in self.flags and on is False:
            self.flags.remove(flag)
        elif flag not in self.flags and on is True:
            self.flags.append(flag)

    def get_flag(self, flag: str):
        return flag in self.flags

    def _deserialize(self, data: dict) -> None:
        if self.channel_type != data.get('type'):
            raise TypeError(f'Channel data is of type `{data.get("type")}` not `{self.channel_type}`')
        self.flags = data.get('flags', self.flags)
        settings = data.get('settings', {})
        for k, v in settings.items():
            self.settings[k] = v

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'server': self.server.id,
            'type': self.channel_type,
            'settings': self.settings,
            'flags': self.flags
        }


class TopicChannel(Channel):
    channel_type = 'topic'
    _default_settings = {
        'tier': 0,
        'saves_in_row': 0,
        'creator': None,
        **super()._default_settings
    }
    _allowed_flags = [
        'MARKED',
        'ARCHIVED',
        *super()._allowed_flags
    ]

    def __init__(self, manager: 'ChannelManager', data: dict):
        super().__init__(manager, data)


Channel_Dict = {
    Channel.channel_type: Channel
}
