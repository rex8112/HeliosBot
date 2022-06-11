import asyncio

import aiohttp
from discord.ext import commands, tasks
from .tools import Config
from typing import Tuple


class HeliosBot(commands.Bot):
    def __init__(self, command_prefix, *, intents, settings: Config, **options):
        self.settings = settings

        super().__init__(command_prefix, intents=intents, **options)

    async def request(self, url_end: str, method='GET'):
        url = f'{self.settings.api_url}{url_end}'
        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                return await session.get(url)
            elif method == 'POST':
                return await session.post(url)
            elif method == 'PUT':
                return await session.put(url)
