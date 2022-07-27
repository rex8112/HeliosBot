from typing import TYPE_CHECKING, Optional

import discord

from .abc import HasSettings
from .exceptions import IdMismatchError
from .tools.settings import Item
from .types.horses import StadiumSerializable
from .types.settings import StadiumSettings

if TYPE_CHECKING:
    from .server import Server
    from .horses.horse import Horse
    from .horses.race import EventRace


class Stadium(HasSettings):
    _default_settings: StadiumSettings = {
        'season': 0,
        'category': None
    }

    def __init__(self, server: 'Server'):
        self.server = server
        self.horses: dict[int, 'Horse'] = {}
        self.races: list['EventRace'] = []
        self.settings: StadiumSettings = self._default_settings.copy()

    @property
    def guild(self) -> discord.Guild:
        return self.server.guild

    @property
    def owner(self) -> discord.Member:
        return self.guild.me

    @property
    def category(self) -> Optional[discord.CategoryChannel]:
        c = self.settings['category']
        if c:
            return c
        else:
            return None

    def serialize(self) -> StadiumSerializable:
        return {
            'server': self.server.id,
            'settings': Item.serialize_dict(self.settings)
        }

    def _deserialize(self, data: StadiumSerializable):
        if data['server'] != self.server.id:
            raise IdMismatchError('This stadium does not belong to this server.')
        self.settings = Item.deserialize_dict(data['settings'], bot=self.server.bot, guild=self.guild)

    async def setup(self, data: StadiumSerializable = None):
        if data is None:
            ...  # data = await self.server.bot.helios_http.get_stadium(self.server.id)

        for hdata in data['horses']:
            h = Horse.from_dict(self, hdata)
            self.horses[h.id] = h

        for rdata in data['races']:
            r = EventRace.from_dict(self, rdata)
            self.races.append(r)
