from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from helios import ChannelManager, HeliosBot


class Channel:
    channel_type = 'Basic'

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
        self.settings = {}
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

    def _deserialize(self, data: dict) -> None:
        if self.channel_type != data.get('type'):
            raise TypeError(f'Channel data is of type {data.get("type")} not {self.channel_type}')
        self.settings = data.get('settings')
        self.flags = data.get('flags')

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'server': self.server.id,
            'type': self.channel_type,
            'settings': self.settings,
            'flags': self.flags
        }
