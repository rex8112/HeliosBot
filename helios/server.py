import asyncio

import discord
from .helios_bot import HeliosBot
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from helios import ServerManager


class Server:
    def __init__(self, bot: HeliosBot, manager: ServerManager, guild: discord.Guild):
        self.loaded = False
        self.bot = bot
        self.guild = guild
        self.manager = manager
        self.channels = {}
        self.private_voice_channels = {}
        self.topics = {}

        self._event = asyncio.Event()

    # Properties
    @property
    def name(self):
        return self.guild.name

    @property
    def id(self):
        return self.guild.id

    # Methods
    async def setup_hook(self):
        # Make asynchronous call to API
        response = await self.bot.request(f'/servers/{self.id}')
        if response.status == 200:
            pass
