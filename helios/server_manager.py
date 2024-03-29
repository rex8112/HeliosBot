import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

import discord

from .server import Server
from .database import ServerModel as ServerModel

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

    async def add_server(self, guild: discord.Guild):
        tasks = []
        server = Server.new(self, guild)
        await server.save()
        tasks.append(server.channels.setup())
        tasks.append(server.members.setup())
        await asyncio.wait(tasks)
        #  await server.stadium.setup()
        self.servers[guild.id] = server
        return server

    async def manage_servers(self):
        cont = True
        while cont:
            for server in self.servers.values():
                tasks = [
                    server.members.manage_members(),
                    server.channels.manage_channels()
                ]
                await asyncio.wait(tasks)
            await asyncio.sleep(60)

    async def setup(self):
        await self.bot.wait_until_ready()
        start_time = time.time()
        tasks = []
        server_data = ServerModel.select()
        server_dict = {}
        for data in server_data:
            server_dict[data.id] = data

        for guild in self.bot.guilds:
            data = server_dict.get(guild.id)
            if data:
                server = Server(self, guild)
                server.deserialize(data)
                channel_data = data.channels
                member_data = data.members
                tasks.append(server.channels.setup(channel_data))
                tasks.append(server.members.setup(member_data))
                #  tasks.append(server.stadium.setup())
            else:
                server = Server.new(self, guild)
                await server.save()
                tasks.append(server.channels.setup())
                tasks.append(server.members.setup())
                #  tasks.append(server.stadium.setup())
            self.servers[server.id] = server

        logger.info(f'{len(self.bot.guilds)} Servers loaded in {time.time() - start_time} seconds')
        start_time = time.time()
        await asyncio.wait(tasks)
        logger.info(f'Channels and Members loaded in {time.time() - start_time} seconds')
        self.bot.loop.create_task(self.manage_servers())
