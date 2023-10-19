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
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import discord

from .playlist import Playlist

if TYPE_CHECKING:
    from .song import Song
    from ..server import Server


class MusicPlayer:
    def __init__(self, server: 'Server'):
        self.server = server
        self.currently_playing: Optional['Song'] = None
        self.playlist = Playlist()
        self._vc: Optional[discord.VoiceClient] = None
        self._started: Optional[datetime] = None
        self._ended: Optional[datetime] = None

    async def join_channel(self, channel: discord.VoiceChannel):
        if self._vc and self._vc.is_connected():
            await self._vc.move_to(channel)
        else:
            self._vc = await channel.connect()

    async def leave_channel(self):
        await self._vc.disconnect()
        self._vc = None
        self.playlist.clear()

    def song_finished(self, exception: Exception):
        if exception:
            return

        next_song = self.playlist.next()
        if next_song is None:
            return
        self.stop_song()
        self.play_song(next_song)

    def play_song(self, song: 'Song') -> bool:
        if self._vc is None:
            return False

        self.currently_playing = song
        self._started = datetime.now().astimezone()
        self._ended = None
        self._vc.play(song.audio_source(), after=lambda x: self.song_finished(x))
        return True

    def stop_song(self):
        if self._vc is None:
            return False
        self._started = None
        self._ended = datetime.now().astimezone()
        self._vc.stop()

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

