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
from datetime import time, timedelta
from typing import TYPE_CHECKING, Optional

import discord

from .song import Song
from .processor import get_info
from ..colour import Colour
from ..views import PaginatorView

if TYPE_CHECKING:
    from ..member import HeliosMember


class Playlist:
    def __init__(self):
        self.songs: list[Song] = []

    def __len__(self):
        return len(self.songs)

    async def add_song_url(self, url: str, requester: 'HeliosMember', *, play_next: bool = False):
        song = await Song.from_url(url, requester=requester)
        if play_next:
            self.add_song_next(song)
        else:
            self.add_song(song)

    def add_song_info(self, info: dict, requester: 'HeliosMember', *, play_next: bool = False):
        song = Song.from_info(info, requester=requester)
        if play_next:
            self.add_song_next(song)
        else:
            self.add_song(song)

    def add_song(self, song: Song):
        self.songs.append(song)

    def add_song_next(self, song: Song):
        self.songs.insert(0, song)

    def get_embed_songs(self, songs: list['Song']) -> list[discord.Embed]:
        song_string = ''
        for song in songs:
            dur = timedelta(seconds=song.duration) if song.duration is not None else 'Unknown Duration'
            song_string += f'**{self.songs.index(song)+1}. {song.title}**By {song.author}\nDuration: {dur}\n\n'
        if not song_string:
            song_string = 'Nothing in queue'
        embed = discord.Embed(
            title='Up Next',
            colour=Colour.music(),
            description=song_string
        )
        return [embed]

    def get_paginator_view(self):
        view = PaginatorView(self.songs, self.get_embed_songs, page_size=5)
        return view

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


def extract_playlist_from_info(data):
    if data.get('_type') == 'playlist':
        if data.get('entries'):
            return [x for x in data.get('entries')]
    return []


class YoutubePlaylist(Playlist):
    def __init__(self, data: dict, requester: 'HeliosMember'):
        super().__init__()
        self.requester = requester
        self.title = data.get('title')
        self.url = data.get('webpage_url')
        thumbnails = data.get('thumbnails', [])
        if thumbnails:
            self.thumbnail = thumbnails[-1].get('url')
        else:
            self.thumbnail = None
        self.songs = [Song.from_info(x, requester=requester, playlist=self) for x in extract_playlist_from_info(data)]
        self.total_duration = sum([x.duration if x.duration is not None else 0 for x in self.songs])

    @classmethod
    async def from_url(cls, url: str, requester: 'HeliosMember'):
        data = await get_info(url, process=False, is_playlist=True)
        return cls(data, requester)
