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
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import discord

from .playlist import Playlist

if TYPE_CHECKING:
    from .song import Song
    from ..server import Server
    from ..member import HeliosMember


class MusicPlayer:
    def __init__(self, server: 'Server'):
        self.server = server
        self.currently_playing: Optional['Song'] = None
        self.playlists: dict[discord.VoiceChannel, Playlist] = {}
        self._vc: Optional[discord.VoiceClient] = None
        self._started: Optional[datetime] = None
        self._ended: Optional[datetime] = None

    @property
    def playlist(self) -> Playlist:
        if self.is_connected():
            playlist = self.playlists.get(self._vc.channel)
            if playlist is None:
                self.playlists[self._vc.channel] = playlist = Playlist()
            return playlist
        else:
            return Playlist()

    async def join_channel(self, channel: discord.VoiceChannel):
        if self.is_connected():
            if self._vc.channel == channel:
                return
            await self._vc.move_to(channel)
        else:
            self._vc = await channel.connect()

    async def leave_channel(self):
        await self._vc.disconnect()
        self._vc = None
        self.playlists.clear()

    def is_connected(self) -> bool:
        return self._vc and self._vc.is_connected()

    async def song_finished(self, exception: Exception) -> None:
        self.stop_song()

        next_song = self.playlist.next()
        if next_song is None:
            return
        if exception or not self.is_connected():
            return
        await self.play_song(next_song)

    async def play_song(self, song: 'Song') -> bool:
        if not self.is_connected():
            return False

        self.currently_playing = song
        self._started = datetime.now().astimezone()
        self._ended = None
        loop = asyncio.get_event_loop()
        self._vc.play(await song.audio_source(), after=lambda x: loop.create_task(self.song_finished(x)), bitrate=64)
        return True

    def stop_song(self) -> bool:
        if not self.is_connected():
            return False
        self.currently_playing = None
        self._started = None
        self._ended = datetime.now().astimezone()
        self._vc.stop()
        return True

    async def add_song_url(self, url: str, requester: 'HeliosMember'):
        await self.playlist.add_song_url(url, requester)
        if self.currently_playing is None:
            await self.play_song(self.playlist.next())

    def seconds_running(self) -> int:
        if self.currently_playing is None:
            return 0
        return int((datetime.now().astimezone() - self._started).total_seconds())

    def time_left(self) -> int:
        if self.currently_playing is None:
            return 0
        duration = self.currently_playing.duration
        seconds_running = self.seconds_running()
        return duration - seconds_running

