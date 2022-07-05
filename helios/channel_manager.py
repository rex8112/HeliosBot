import logging
import time
from typing import TYPE_CHECKING, Optional

from .channel import Channel_Dict, Channel

if TYPE_CHECKING:
    from .server import Server
    from .helios_bot import HeliosBot
logger = logging.getLogger('HeliosLogger')


class ChannelManager:
    def __init__(self, server: 'Server'):
        self.bot: 'HeliosBot' = server.bot
        self.server = server
        self.channels: dict[int, Channel] = {}

    def get(self, channel_id: int) -> Optional[Channel]:
        return self.channels.get(channel_id)

    async def setup(self, channel_data: list[dict] = None):
        start_time = time.time()
        tasks = []
        if not channel_data:
            data = await self.bot.http.get_channel(server=self.server.id)
            channel_data = data

        for data in channel_data:
            c = Channel(self, data)
            self.channels[c.id] = c
