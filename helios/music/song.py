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

from typing import TYPE_CHECKING

from .processor import YtProcessor

__all__ = ('Song',)

if TYPE_CHECKING:
    from ..member import HeliosMember


class Song:
    def __init__(self, title: str, url: str, duration: int, *, requester: 'HeliosMember' = None):
        self.title = title
        self.url = url
        self.duration = duration
        self.requester = requester

    def __eq__(self, other):
        if isinstance(other, Song):
            return self.url == other.url
        return NotImplemented

    @classmethod
    async def from_url(cls, url: str, *, requester: 'HeliosMember' = None):
        data = await YtProcessor.get_info(url, process=False)
        return cls(data['title'], data['webpage_url'], data['duration'], requester=requester)

    async def audio_source(self):
        return await YtProcessor.get_audio_source(self.url)
