import asyncio
import logging
from typing import TYPE_CHECKING, Optional

import discord

from .channel import Channel_Dict, Channel, VoiceChannel
from .database import ChannelModel, update_model_instance

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

        self._task = None

    def get(self, channel_id: int) -> Optional[Channel]:
        return self.channels.get(channel_id)

    def get_type(self, t: str) -> list['HeliosChannel']:
        return list(filter(lambda x: x.channel_type == t, self.channels.values()))

    def _add_channel(self, channel: 'HeliosChannel'):
        if self.get(channel.id):
            raise NotImplemented
        self.channels[channel.id] = channel

    def create_run_task(self):
        if not self._task:
            self._task = self.bot.loop.create_task(self.manage_channels(), name=f'{self.server.id}: Channel Manager')

    async def manage_channels(self):
        await self.bot.wait_until_ready()
        await self.purge_dead_channels()
        await self.manage_topics()
        await self.manage_voices()

    async def purge_dead_channels(self):
        deletes = []
        deletes_keys = []
        for k, v in self.channels.items():
            if v.alive is False:
                deletes_keys.append(k)
                deletes.append(v.delete(del_channel=False))
        if len(deletes) > 0:
            await asyncio.wait(deletes)
            for k in deletes_keys:
                del self.channels[k]

    async def manage_topics(self):
        """Run evaluate_tiers and evaluate_state on all topic channels."""
        topic_channels = self.get_type('topic')
        e_tiers = []
        e_state = []
        e_save = []
        for c in topic_channels:
            e_tiers.append(c.evaluate_tier())
            e_state.append(c.evaluate_state())
            e_save.append(c.save())
        if len(e_tiers) > 0:
            logger.debug(f'{self.server.name}: Evaluating Topic Tiers')
            await asyncio.wait(e_tiers)
            logger.debug(f'{self.server.name}: Evaluating Topic States')
            await asyncio.wait(e_state)
            await asyncio.wait(e_save)

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
            await asyncio.wait(delete)
        if neutralize:
            await asyncio.wait(neutralize)
            await asyncio.wait(save)
        if update_message:
            await asyncio.wait(update_message)

    async def add_topic(self, channel: discord.TextChannel, owner: discord.User, tier=1) -> tuple[bool, str]:
        if self.channels.get(channel.id):
            return False, 'This channel already exists.'
        channel_type = Channel_Dict.get('topic')
        ch = channel_type.new(self, channel.id)
        ch.settings.creator = owner.id
        ch.settings.tier = tier
        self._add_channel(ch)
        await ch.save()
        return True, 'Created Successfully!'

    async def create_topic(self, name: str, owner: discord.User) -> tuple[bool, str]:
        topics = self.get_type('topic')
        for t in topics:
            if t.channel.name.lower() == name.lower():
                return False, f'Channel already exists: {t.channel.mention}'
        category = self.bot.get_channel(self.server.settings.topic_category)
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
        if not channel_data:
            data = ChannelModel.select().where(ChannelModel.server == self.server.id)
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
        if len(deletes) > 0:
            await asyncio.wait(deletes)
        if neutralize:
            await asyncio.wait(neutralize)
        logger.debug(f'Adding {self.server.id}: Channel Manager to event loop')
        #  self.create_run_task()
