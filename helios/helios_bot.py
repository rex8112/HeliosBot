import asyncio

import aiohttp
from discord.ext import commands, tasks
from .tools import Config
from typing import Tuple


class HeliosBot(commands.Bot):
    def __init__(self, command_prefix, *, intents, settings: Config, **options):
        self.settings = settings
        self._session = aiohttp.ClientSession()

        super().__init__(command_prefix, intents=intents, **options)