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

from typing import TYPE_CHECKING, Optional

import discord

from .song import Song

if TYPE_CHECKING:
    from ..member import HeliosMember


class Playlist:
    def __init__(self):
        self.songs: list[Song] = []

    def __len__(self):
        return len(self.songs)

    async def add_song_url_next(self, url: str, requester: 'HeliosMember'):
        song = await Song.from_url(url, requester=requester)
        self.songs.insert(0, song)

    async def add_song_url(self, url: str, requester: 'HeliosMember'):
        song = await Song.from_url(url, requester=requester)
        self.songs.append(song)

    def next(self):
        try:
            return self.songs.pop(0)
        except IndexError:
            return None

    def total_duration(self):
        seconds = 0
        for song in self.songs:
            seconds += song.duration
        return seconds

    def clear(self):
        self.songs.clear()
