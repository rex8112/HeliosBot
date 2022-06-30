import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

from .server import Server

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
logger = logging.getLogger('HeliosLogger')


class ServerManager:
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.servers: dict[int, Server] = {}
        self.channel_refresh_queue = asyncio.Queue()

    def get(self, guild_id: int) -> Optional[Server]:
        return self.servers.get(guild_id)

    async def setup(self):
        start_time = time.time()
        tasks = []
        for guild in self.bot.guilds:
            tasks.append(asyncio.ensure_future(self.bot.http.get_server(guild.id)))
            server = Server(self.bot, self, guild)
            self.servers[server.id] = server

        servers_data = await asyncio.gather(*tasks)
        for data in servers_data:
            if data.get('detail') is None:
                server: Server = self.servers.get(data.get('id'))
                server.deserialize(data)
                await self.channel_refresh_queue.put(server)
        logger.info(f'{len(tasks)} Servers loaded in {time.time() - start_time} seconds')
