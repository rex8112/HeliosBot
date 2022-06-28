import asyncio

import aiohttp
import logging
from discord.ext import commands, tasks

from .server_manager import ServerManager
from .tools import Config
from .http import HTTPClient
from .server import Server
from typing import Tuple

logger = logging.getLogger('HeliosLogger')


class HeliosBot(commands.Bot):
    def __init__(self, command_prefix, *, intents, settings: Config, **options):
        self.servers = ServerManager(self)
        self.settings = settings
        self.ready_once = True
        self.http = HTTPClient(self.settings.api_url, self.settings.api_username, self.settings.api_password)

        super().__init__(command_prefix, intents=intents, **options)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        if self.ready_once:
            logger.debug('Beginning server load')
            await self.servers.setup()
            self.ready_once = False
