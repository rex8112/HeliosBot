from typing import TYPE_CHECKING, Optional

import discord

from .abc import HasSettings

if TYPE_CHECKING:
    from .server import Server


class Stadium(HasSettings):
    _default_settings = {
        'season': 0,
        'category': None
    }

    def __init__(self, server: 'Server'):
        self.server = server

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
            if isinstance(c, discord.CategoryChannel):
                return c
            else:
                return self.guild.get_channel(c)
        else:
            return None
