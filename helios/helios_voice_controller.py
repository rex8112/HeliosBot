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
from datetime import datetime

from typing import TYPE_CHECKING, Optional, Awaitable

import discord
from discord.utils import utcnow

from .tools.async_event import AsyncEvent

if TYPE_CHECKING:
    from .server import Server
    from .helios_bot import HeliosBot
    from .member import HeliosMember


class HeliosVoiceController:
    def __init__(self, server: 'Server'):
        self.server = server
        self.bot: 'HeliosBot' = server.bot
        self.voice_client: Optional[discord.VoiceClient] = None
        self.last_start: Optional[datetime] = None
        self.last_end: Optional[datetime] = None
        self.in_use = False

        self.connect_event = AsyncEvent()
        self.disconnect_event = AsyncEvent()
        self.on_connect = self.connect_event.on
        self.on_disconnect = self.disconnect_event.on

        self._current_audio = None
        self._task = None

    async def connect(self, channel: discord.VoiceChannel) -> discord.VoiceClient:
        """Connect to a voice channel."""
        attempts = 0
        while attempts < 5:
            try:
                if self.voice_client:
                    await self.voice_client.move_to(channel)
                else:
                    self.voice_client = await channel.connect()
            except asyncio.TimeoutError:
                attempts += 1
            else:
                await self.connect_event(channel)
                return self.voice_client
        self.voice_client = None
        raise ConnectionError('Failed to connect to voice channel.')

    async def disconnect(self) -> bool:
        """Disconnect from the voice channel."""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
            await self.disconnect_event()
            return True
        return False

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