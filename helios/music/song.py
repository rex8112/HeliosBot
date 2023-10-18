from typing import TYPE_CHECKING

from .processor import YtProcessor

__all__ = ('Song',)

if TYPE_CHECKING:
    from ..member import HeliosMember


class Song:
    def __init__(self, title: str, url: str, raw_url: str, duration: int, *, requester: 'HeliosMember' = None):
        self.title = title
        self.url = url
        self.raw_url = raw_url
        self.duration = duration
        self.requester = requester

    def __eq__(self, other):
        if isinstance(other, Song):
            return self.url == other.url
        return NotImplemented

    @classmethod
    async def from_url(cls, url: str, *, requester: 'HeliosMember' = None):
        data = await YtProcessor.get_info(url)
        return cls(data['title'], data['webpage_url'], data['url'], data['duration'], requester=requester)

    def audio_source(self):
        return YtProcessor.get_audio_source_from_raw(self.raw_url)
