from typing import TYPE_CHECKING

import discord

from .abc import HasSettings

if TYPE_CHECKING:
    from .server import Server


class Stadium(HasSettings):
    _default_settings = {

    }

    def __init__(self, server: 'Server'):
        self.server = server

    @property
    def guild(self) -> discord.Guild:
        return self.server.guild

    @property
    def owner(self) -> discord.Member:
        return self.guild.me
