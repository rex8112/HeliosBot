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

from typing import TYPE_CHECKING, Union

from .processor import *

__all__ = ('Song',)

if TYPE_CHECKING:
    from .playlist import YoutubePlaylist
    from ..member import HeliosMember


class Song:
    def __init__(self, title: str, author: str, url: str, duration: int, thumbnail: str, *,
                 requester: 'HeliosMember' = None, playlist: 'YoutubePlaylist' = None, cost: int = None):
        self.title = title
        self.author = author
        self.url = url
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester
        self.playlist = playlist
        self.cost = cost
        self.vote_skip = set()
        self.tips = 0

        self.finished = asyncio.Event()

    def __eq__(self, other):
        if isinstance(other, Song):
            return self.url == other.url
        return NotImplemented

    def __hash__(self):
        return hash(self.url)

    def percentage(self, time: int):
        """Get the percentage of the song that has been played."""
        return time / self.duration

    def calculate_full_song_cost(self) -> int:
        """Calculate the full cost of the song."""
        duration = self.duration
        if duration is None:
            return 0
        if self.requester:
            # cost_per_minute = self.requester.server.settings.music_points_per_minute.value
            cost_per_minute = 0
        else:
            cost_per_minute = 0
        return int((duration * cost_per_minute) / 60)

    def calculate_cost(self, time: int) -> int:
        """Calculate the cost of the song based on the time played."""
        full_cost = self.calculate_full_song_cost()
        return int(self.percentage(time) * full_cost)

    @classmethod
    async def from_url(cls, url: str, *, requester: 'HeliosMember' = None, playlist: 'YoutubePlaylist' = None):
        data = await get_info(url, process=False)
        return cls.from_info(data, requester=requester, playlist=playlist) if data is not None else None

    @classmethod
    def from_info(cls, info: dict, *, requester: 'HeliosMember' = None, playlist: 'YoutubePlaylist' = None):
        url = info['url'] if 'url' in info else info['webpage_url']
        thumbnail = info['thumbnails'][-1]['url'] if 'thumbnails' in info else info['thumbnail']
        return cls(info['title'], info['uploader'], url, info['duration'], thumbnail,
                   requester=requester, playlist=playlist)

    async def audio_source(self, *, start: Union[int, float] = 0):
        return await get_audio_source(self.url, start=start)

    async def wait(self):
        await self.finished.wait()

    def set_finished(self):
        self.finished.set()

    def set_unfinished(self):
        self.finished.clear()
