from typing import TYPE_CHECKING, Optional

import discord

from .song import Song

if TYPE_CHECKING:
    from ..member import HeliosMember


class Playlist:
    def __init__(self):
        self.songs: list[Song] = []

    async def add_song_url(self, url: str, requester: 'HeliosMember'):
        song = await Song.from_url(url, requester=requester)
        self.songs.append(song)
