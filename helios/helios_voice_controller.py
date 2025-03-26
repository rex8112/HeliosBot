#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
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
from datetime import datetime
from types import MethodType

from typing import TYPE_CHECKING, Optional, Awaitable

import discord
from discord.utils import utcnow
from discord.ext.tasks import loop

from .music import MusicPlayer
from .tools.async_event import AsyncEvent
from .voice_scheduler import Schedule, TimeSlot

if TYPE_CHECKING:
    from .server import Server
    from .helios_bot import HeliosBot
    from .member import HeliosMember


logger = logging.getLogger('Helios.VoiceController')


class HeliosVoiceController:
    def __init__(self, server: 'Server'):
        self.server = server
        self.bot: 'HeliosBot' = server.bot
        self.voice_client: Optional[discord.VoiceClient] = None
        self.last_start: Optional[datetime] = None
        self.last_end: Optional[datetime] = None
        self.in_use = False
        self.schedule = Schedule()

        self.connect_event = AsyncEvent()
        self.disconnect_event = AsyncEvent()
        self.on_connect = self.connect_event.on
        self.on_disconnect = self.disconnect_event.on

        self.schedule.add_handler('music', lambda slot: self.start_music(slot))
        self.schedule.add_handler('music_end', lambda slot: self.stop_music(slot))

        self._current_audio = None
        self._task = None
        self._on_voice_wrapper = None

    def start(self):
        async def on_voice_wrapper(member, before, after):
            await self.on_voice_state_update(member, before, after)
        self._on_voice_wrapper = on_voice_wrapper
        self.schedule.start()
        self.check_vc.start()
        self.server.bot.add_listener(self.on_voice_state_update, 'on_voice_state_update')

    def stop(self):
        self.schedule.stop()
        self.check_vc.stop()
        self.server.bot.remove_listener(self.on_voice_state_update, 'on_voice_state_update')

    async def play_music(self, interaction: discord.Interaction, *args, dont_start_music=False):
        slot = self.schedule.current_slot()
        if slot and slot.type == 'music':
            music_player: 'MusicPlayer' = slot.data['music_player']
            await music_player.member_play(interaction, *args)
        else:
            if dont_start_music:
                await interaction.response.defer(ephemeral=True)
                data = {'channel_id': interaction.channel.id}
            else:
                data = {'channel_id': interaction.channel.id, 'interaction': interaction}
            if args:
                data['url'] = args[0]

            self.schedule.create_now_slot(5*60, 'music', data)

    async def start_music(self, slot: TimeSlot):
        if self.in_use:
            return False
        self.claim()
        channel_id = slot.data['channel_id']
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return False
        interaction = slot.data.get('interaction')
        start_url = slot.data.get('url')
        requester_id = slot.data.get('requester_id')
        requester = self.server.members.get(requester_id)
        await self.connect(channel)
        music_player = MusicPlayer(self, self.schedule, slot)
        slot.data['music_player'] = music_player
        music_player.start()
        if start_url and interaction:
            await music_player.member_play(interaction, start_url)

    async def stop_music(self, slot: TimeSlot):
        self.release()
        music_player = slot.data['music_player']

        music_player.stop()
        await self.disconnect()

    async def connect(self, channel: discord.VoiceChannel) -> discord.VoiceClient:
        """Connect to a voice channel."""
        attempts = 0
        while attempts < 5:
            try:
                if self.voice_client and self.voice_client.is_connected():
                    await self.voice_client.move_to(channel)
                else:
                    self.voice_client: discord.VoiceClient = await channel.connect()
            except (asyncio.TimeoutError, discord.ClientException):
                attempts += 1
                await asyncio.sleep(1)
            else:
                await self.connect_event(channel)
                return self.voice_client
        self.voice_client = None
        raise ConnectionError('Failed to connect to voice channel.')

    async def disconnect(self) -> bool:
        """Disconnect from the voice channel."""
        if self.voice_client:
            try:
                await self.voice_client.disconnect()
            except Exception as e:
                logger.error(f'Error disconnecting from voice channel: {e}')
            self.voice_client = None
            await self.disconnect_event()
            return True
        return False

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member != self.server.guild.me:
            return
        if before.channel == after.channel:
            return
        if not self.in_use:
            return
        if before.channel and before.channel.guild == self.server.guild:
            if after.channel is None:
                await self.bot_on_disconnect(before.channel)
            elif after.channel.id != self.schedule.current_slot().data.get('channel_id'):
                await asyncio.sleep(1)
                channel = self.bot.get_channel(self.schedule.current_slot().data.get('channel_id'))
                await self.connect(channel)

    async def bot_on_disconnect(self, channel: discord.VoiceChannel):
        if self.voice_client:
            if self.in_use:
                try:
                    await self.connect(channel)
                except ConnectionError:
                    if self.schedule.current_slot():
                        self.schedule.current_slot().end = datetime.now().astimezone()

            else:
                self.voice_client = None
                await self.disconnect_event()

    @loop(seconds=5)
    async def check_vc(self):
        if self.schedule.current_slot():
            channel = self.bot.get_channel(self.schedule.current_slot().data.get('channel_id'))
            if self.voice_client and self.voice_client.guild.me in channel.members and len(channel.members) <= 1:
                self.schedule.current_slot().end = datetime.now().astimezone()

    def claim(self):
        """Claim the voice controller for use."""
        if self.in_use:
            raise ValueError('Voice controller already in use.')
        self.in_use = True

    def release(self):
        """Release the voice controller for use."""
        if not self.in_use:
            raise ValueError('Voice controller not in use.')
        self.in_use = False

    def play(self, source: discord.FFmpegPCMAudio) -> Awaitable[None]:
        """Play an audio source."""
        if not self.voice_client:
            raise ValueError('Voice client not connected.')
        future = asyncio.get_event_loop().create_future()

        def done(exc: Optional[Exception] = None):
            if exc:
                future.set_exception(exc)
            else:
                future.set_result(None)
            self.last_end = utcnow()

        self._current_audio = source
        self.last_start = utcnow()
        self.last_end = None
        self.voice_client.play(source, after=done, bitrate=64)
        return future