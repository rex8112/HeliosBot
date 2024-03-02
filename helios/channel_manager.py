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

from .channel import Channel_Dict, Channel, VoiceChannel
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


class ChannelManager:
    def __init__(self, server: 'Server'):
        self.bot: 'HeliosBot' = server.bot
        self.server = server
        self.channels: dict[int, 'HeliosChannel'] = {}
        self.topic_channels: dict[int, TopicChannel] = {}
        self.dynamic_voice = VoiceManager(self.server)

        self._task = None

    def get(self, channel_id: int) -> Optional[Union[Channel, TopicChannel]]:
        channel = self.channels.get(channel_id)
        if not channel:
            channel = self.topic_channels.get(channel_id)
        return channel

    def get_type(self, t: str) -> list['HeliosChannel']:
        return list(filter(lambda x: x.channel_type == t, self.channels.values()))

    def _add_channel(self, channel: Union['HeliosChannel', 'TopicChannel']):
        if self.get(channel.id):
            raise NotImplemented
        if isinstance(channel, TopicChannel):
            self.topic_channels[channel.id] = channel
        else:
            self.channels[channel.id] = channel

    def create_run_task(self):
        if not self._task:
            self._task = self.bot.loop.create_task(self.manage_channels(), name=f'{self.server.id}: Channel Manager')

    def is_crowded(self):
        topics = self.get_type('topic')
        counter = 0
        for topic in topics:
            if 'ARCHIVED' not in topic.flags:
                counter += 1
        return counter > 10

    async def manage_channels(self):
        await self.bot.wait_until_ready()
        await self.purge_dead_channels()
        await self.manage_topics()
        await self.manage_voices()

        logger.debug(f'{self.server.name}: Channel Manager: Running Dynamic Voice Check')
        await self.dynamic_voice.check_channels()
        logger.debug(f'{self.server.name}: Channel Manager: Dynamic Voice Check Complete')

    async def purge_dead_channels(self):
        deletes = []
        deletes_keys = []
        for k, v in self.channels.items():
            if v.alive is False:
                deletes_keys.append(k)
                deletes.append(v.delete(del_channel=False))
        for k, v in self.topic_channels.items():
            if v.alive is False:
                deletes_keys.append(k)
                deletes.append(v.delete(del_channel=False))
        if len(deletes) > 0:
            await asyncio.gather(*deletes)
            for k in deletes_keys:
                try:
                    del self.channels[k]
                except KeyError:
                    ...
                try:
                    del self.topic_channels[k]
                except KeyError:
                    ...

    async def manage_topics(self):
        """Get channel points, sort by them and evaluate_state on the lower channels after the tenth channel."""
        topic_channels = list(filter(lambda x: x.active_only or x.pending, self.topic_channels.values()))
        pinned = list(filter(lambda x: x.pinned, self.topic_channels.values()))
        if len(topic_channels) == 0:
            return
        e_values = []
        e_state = []
        e_save = []
        for c in topic_channels:
            e_values.append(c.get_points())
        await asyncio.gather(*e_values)
        topic_channels.sort(key=lambda x: x.points if not x.pending else 0, reverse=True)

        for i, c in enumerate(topic_channels):
            if i > 9 or c.pending:
                e_state.append(c.evaluate_state())
                e_save.append(c.save())
        if e_state:
            await asyncio.gather(*e_state)
            await asyncio.gather(*e_save)

        topic_channels = pinned + topic_channels
        for i, c in enumerate(topic_channels, start=1):
            if c.channel.position != i:
                logger.debug(f'{c.channel.name} is at {c.channel.position} should be at {i}')
                await c.channel.edit(position=i)

    async def manage_voices(self):
        voice_channels: list[VoiceChannel] = self.get_type('private_voice')
        neutralize = []
        delete = []
        save = []
        update_message = []
        for v in voice_channels:
            if v.can_delete():
                delete.append(v.delete())
            elif v.can_neutralize():
                neutralize.append(v.neutralize())
                save.append(v.save())
                update_message.append(v.update_message())
            else:
                update_message.append(v.update_message())
        if delete:
            await asyncio.gather(*delete)
        if neutralize:
            await asyncio.gather(*neutralize)
            await asyncio.gather(*save)
        if update_message:
            await asyncio.gather(*update_message)

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
        category = self.bot.get_channel(self.server.settings.topic_category.value.id)
        if category:
            new_channel = await category.create_text_channel(name=name)
            channel = TopicChannel(self.server, new_channel)
            channel.creator = owner
            self._add_channel(channel)
            await channel.save()
            return True, f'{channel.channel.mention} created successfully!'
        else:
            return False, 'This server does not have `Topic Channel Creation` enabled.'

    async def create_private_voice(self, owner: 'HeliosMember', *,
                                   template: 'VoiceTemplate') -> VoiceChannel:
        if self.server.private_create_channel:
            category = self.server.private_create_channel.category
            channel = await category.create_voice_channel(
                name=template.name,
                overwrites=template.overwrites
            )
            voice = VoiceChannel.new(self, channel.id)
            voice.owner = owner
            voice.template_name = template.name
            await voice.update_message()
            self._add_channel(voice)

            return voice

    async def setup(self, channel_data: list[dict] = None):
        await self.dynamic_voice.setup()
        if not channel_data:
            q = ChannelModel.select().where(ChannelModel.server == self.server.id)
            data = await objects.prefetch(q)
            channel_data = data

        deletes = []
        neutralize = []
        for data in channel_data:
            channel_cls = Channel_Dict.get(data.type)
            c: 'HeliosChannel' = channel_cls(self, data)
            if c.alive:
                self.channels[c.id] = c
                if isinstance(c, VoiceChannel):
                    if c.can_neutralize():
                        neutralize.append(c.neutralize())
            else:
                deletes.append(c.delete(del_channel=False))

        topic_channels = await TopicChannel.get_all(self.server)
        for t in topic_channels:
            if t and t.alive:
                self.topic_channels[t.id] = t
            else:
                deletes.append(t.delete(del_channel=False))

        if len(deletes) > 0:
            await asyncio.gather(*deletes)
        if neutralize:
            await asyncio.gather(*neutralize)
        logger.debug(f'Adding {self.server.id}: Channel Manager to event loop')
        #  self.create_run_task()
