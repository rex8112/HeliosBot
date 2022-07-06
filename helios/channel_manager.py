import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

import discord

from .channel import Channel_Dict, Channel

if TYPE_CHECKING:
    from .server import Server
    from .helios_bot import HeliosBot
    from .types import HeliosChannel
logger = logging.getLogger('HeliosLogger')


class ChannelManager:
    def __init__(self, server: 'Server'):
        self.bot: 'HeliosBot' = server.bot
        self.server = server
        self.channels: dict[int, HeliosChannel] = {}

    def get(self, channel_id: int) -> Optional[Channel]:
        return self.channels.get(channel_id)

    def get_type(self, t: str) -> list[HeliosChannel]:
        return list(filter(lambda x: x.type == t, self.channels.values()))

    def _add_channel(self, channel: HeliosChannel):
        if self.get(channel.id):
            raise NotImplemented
        self.channels[channel.id] = channel

    async def manage_channels(self):
        while True:
            await self.purge_dead_channels()
            await self.manage_topics()

            await asyncio.sleep(60)

    async def purge_dead_channels(self):
        deletes = []
        for k, v in self.channels.items():
            if v.alive is False:
                del self.channels[k]
                deletes.append(v.delete(del_channel=False))
        await asyncio.wait(deletes)

    async def manage_topics(self):
        """Run evaluate_tiers and evaluate_state on all topic channels."""
        topic_channels = self.get_type('topic')
        e_tiers = []
        e_state = []
        for c in topic_channels:
            e_tiers.append(c.evaluate_tier())
            e_state.append(c.evaluate_state())
        logger.debug(f'{self.server.name}: Evaluating Topic Tiers')
        await asyncio.wait(e_tiers)
        logger.debug(f'{self.server.name}: Evaluating Topic States')
        await asyncio.wait(e_state)

    async def create_topic(self, name: str, owner: discord.User) -> tuple[bool, str]:
        topics = self.get_type('topic')
        for t in topics:
            if t.channel.name.lower() == name.lower():
                return False, f'Channel already exists: {t.channel.mention}'
        category = self.bot.get_channel(self.server.settings.get('topic_category'))
        if category:
            new_channel = await category.create_text_channel(name=name)
            channel_type = Channel_Dict.get('topic')
            channel = channel_type.new(self, new_channel.id)
            channel.settings['creator'] = owner.id
            self._add_channel(channel)
            await channel.save()
            return True, f'{channel.channel.mention} created successfully!'
        else:
            return False, 'This server does not have `Topic Channel Creation` enabled.'

    async def setup(self, channel_data: list[dict] = None):
        if not channel_data:
            data = await self.bot.helios_http.get_channel(server=self.server.id)
            channel_data = data

        deletes = []
        for data in channel_data:
            channel_cls = Channel_Dict.get(data.get('type'))
            c: 'HeliosChannel' = channel_cls(self, data)
            if c.alive:
                self.channels[c.id] = c
            else:
                deletes.append(c.delete(del_channel=False))
        await asyncio.wait(deletes)
        logger.debug(f'Adding {self.server.id}: Channel Manager to event loop')
        self.bot.loop.create_task(self.manage_channels(), name=f'{self.server.id}: Channel Manager')
