import asyncio

import aiohttp
import logging
from discord.ext import commands, tasks

from .server_manager import ServerManager
from .tools import Config
from .server import Server
from typing import Tuple

logger = logging.getLogger('HeliosLogger')


class HeliosBot(commands.Bot):
    def __init__(self, command_prefix, *, intents, settings: Config, **options):
        self.servers = ServerManager(self)
        self.settings = settings
        self.ready_once = True

        super().__init__(command_prefix, intents=intents, **options)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        if self.ready_once:
            logger.debug('Beginning server load')
            await self.servers.setup()
            self.ready_once = False

    async def request(self, url_end: str, method='GET'):
        url = f'{self.settings.api_url}{url_end}'
        async with aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(self.settings.api_username, self.settings.api_password)
        ) as session:
            if method == 'GET':
                return await session.get(url)
            elif method == 'POST':
                return await session.post(url)
            elif method == 'PUT':
                return await session.put(url)
