import logging
from typing import Optional

from discord.ext import commands

from .http import HTTPClient
from .server_manager import ServerManager
from .tools import Config

logger = logging.getLogger('HeliosLogger')


class HeliosBot(commands.Bot):
    def __init__(self, command_prefix, *, intents, settings: Config, **options):
        self.servers = ServerManager(self)
        self.settings = settings
        self.ready_once = True
        self.helios_http: Optional[HTTPClient] = None

        super().__init__(command_prefix, intents=intents, **options)

    async def setup_hook(self) -> None:
        self.helios_http = HTTPClient(
            self.settings.api_url,
            loop=self.loop,
            api_username=self.settings.api_username,
            api_password=self.settings.api_password
        )

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        if self.ready_once:
            logger.debug('Beginning server load')
            await self.servers.setup()
            self.ready_once = False
