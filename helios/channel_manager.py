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

import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Union

import discord

from .database import ChannelModel, objects
from .dynamic_voice import VoiceManager
from .topics import TopicChannel

if TYPE_CHECKING:
    from .server import Server
    from .helios_bot import HeliosBot
    from .member import HeliosMember
    from .types import HeliosChannel
    from .voice_template import VoiceTemplate
logger = logging.getLogger('HeliosLogger')


def need_sorting(all_channels):
    discord_channels = all_channels[0].channel.category.text_channels
    for i, channel in enumerate(all_channels):
        if channel.channel != discord_channels[i]:
            return True
    return False


class ChannelManager:
    def __init__(self, server: 'Server'):
        self.bot: 'HeliosBot' = server.bot
        self.server = server
        self.topic_channels: dict[int, TopicChannel] = {}
        self.dynamic_voice = VoiceManager(self.server)

        self._task = None

    def get(self, channel_id: int) -> Optional[Union[TopicChannel]]:
        channel = self.topic_channels.get(channel_id)
        if channel is None:
            channel = self.dynamic_voice.channels.get(channel_id)
        return channel

    def get_topic_by_name(self, name: str) -> Optional[TopicChannel]:
        for channel in self.topic_channels.values():
            if channel.channel.name == name:
                return channel
            if channel.channel.name.replace('🛑', '') == name:
                return channel
        return

    def _add_channel(self, channel: Union['HeliosChannel', 'TopicChannel']):
        if self.get(channel.id):
            raise NotImplemented
        if isinstance(channel, TopicChannel):
            self.topic_channels[channel.id] = channel

    async def manage_channels(self):
        await self.bot.wait_until_ready()
        await self.purge_dead_channels()
        logger.debug(f'{self.server.name}: Channel Manager: Manage Topics')
        await self.manage_topics()
        logger.debug(f'{self.server.name}: Channel Manager: Manage Topics Complete')

        logger.debug(f'{self.server.name}: Channel Manager: Running Dynamic Voice Check')
        await self.dynamic_voice.check_channels()
        logger.debug(f'{self.server.name}: Channel Manager: Dynamic Voice Check Complete')

    async def purge_dead_channels(self):
        deletes = []
        deletes_keys = []
        for k, v in self.topic_channels.items():
            if v.alive is False:
                deletes_keys.append(k)
                deletes.append(v.delete(del_channel=False))
        for k, v in self.dynamic_voice.channels.items():
            if v.alive is False:
                deletes_keys.append(k)
                deletes.append(v.delete())
        if len(deletes) > 0:
            await asyncio.gather(*deletes)
            for k in deletes_keys:
                try:
                    del self.topic_channels[k]
                except KeyError:
                    ...
        roles: list[discord.Role] = list(filter(lambda x: x.name.endswith('_sub'), self.server.guild.roles))
        for role in roles:
            if not self.get_topic_by_name(role.name[:-4]):
                await role.delete()

    async def manage_topics(self):
        """Get channel points, sort by them and evaluate_state on the lower channels after the tenth channel."""
        topic_channels = list(filter(lambda x: x.active_only, self.topic_channels.values()))
        pending_channels = list(filter(lambda x: x.pending, self.topic_channels.values()))
        pinned = list(filter(lambda x: x.pinned, self.topic_channels.values()))
        if len(topic_channels) == 0:
            return
        e_values = []
        e_state = []
        e_save = []
        for c in topic_channels:
            e_values.append(c.get_points())
        await asyncio.gather(*e_values)
        topic_channels.sort(key=lambda x: (x.points, x.channel.name), reverse=True)
        topic_channels = topic_channels + pending_channels

        save = []
        logger.debug(f'{self.server.name}: {topic_channels}')
        for i, c in enumerate(topic_channels):
            if i > self.server.settings['topic_soft_cap'] - 1 or c.pending:
                logger.debug(f'{self.server.name}: {i} - {c.pending}')
                e_state.append(c.evaluate_state())
                save.append(c)
        if e_state:
            logger.debug(f'{self.server.name}: Channel Manager: Evaluating States')
            await asyncio.gather(*e_state)
            logger.debug(f'{self.server.name}: Channel Manager: Saving States')
            tasks = []
            for c in save:
                tasks.append(c.save())
            await asyncio.gather(*tasks)

        topic_channels = pinned + topic_channels
        if need_sorting(topic_channels):
            for i, c in enumerate(topic_channels):
                if c.channel.position != i:
                    logger.debug(f'{c.channel.name} is at {c.channel.position} should be at {i}')
                    await c.channel.edit(position=i)

    async def add_topic(self, channel: discord.TextChannel, owner: 'HeliosMember') -> tuple[bool, str]:
        if self.channels.get(channel.id):
            return False, 'This channel is already important.'
        category = self.bot.get_channel(self.server.settings.topic_category.value.id)
        if category:
            await channel.edit(category=category, sync_permissions=True)
        ch = TopicChannel(self.server, channel)
        ch.creator = owner
        self._add_channel(ch)
        await ch.save()
        return True, 'Added Successfully!'

    async def create_topic(self, name: str, owner: 'HeliosMember') -> tuple[bool, str]:
        topics = self.topic_channels.values()
        for t in topics:
            if t.channel.name.lower() == name.lower().replace(' ', '-'):
                return False, f'Channel already exists: {t.channel.mention}'
        if self.server.settings.topic_category.value is not None:
            category = self.bot.get_channel(self.server.settings.topic_category.value.id)
        else:
            category = None
        if category:
            new_channel = await category.create_text_channel(name=name)
            channel = TopicChannel(self.server, new_channel)
            channel.creator = owner
            self._add_channel(channel)
            await channel.save()
            await channel.create_role()
            await channel.channel.edit(topic=channel.get_description())
            return True, f'{channel.channel.mention} created successfully!'
        else:
            return False, 'This server does not have `Topic Channel Creation` enabled.'

    async def setup(self, channel_data: list[dict] = None):
        await self.dynamic_voice.setup()
        if not channel_data:
            q = ChannelModel.select().where(ChannelModel.server == self.server.id)
            data = await objects.prefetch(q)
            channel_data = data

        deletes = []
        neutralize = []

        topic_channels = await TopicChannel.get_all(self.server)
        for t in topic_channels:
            if t and t.alive:
                self.topic_channels[t.id] = t
                if t.active or t.pending:
                    role = t.get_role()
                    if not role:
                        await t.create_role()
            else:
                deletes.append(t.delete(del_channel=False))

        if len(deletes) > 0:
            await asyncio.gather(*deletes)
        if neutralize:
            await asyncio.gather(*neutralize)
        logger.debug(f'Adding {self.server.id}: Channel Manager to event loop')
        #  self.create_run_task()
