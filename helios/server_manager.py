#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

import discord

from .database import ServerModel, MemberModel, ChannelModel, objects
from .server import Server
from .views import ShopView

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
        await asyncio.gather(*tasks)
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
                await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(15)

    async def setup(self):
        await self.bot.wait_until_ready()
        start_time = time.time()
        tasks = []
        q = ServerModel.select()
        server_data = await objects.prefetch(q, MemberModel.select(), ChannelModel.select())
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
            self.bot.add_view(ShopView(server))
            await server.theme.load()

        logger.info(f'{len(self.bot.guilds)} Servers loaded in {time.time() - start_time} seconds')
        start_time = time.time()
        await asyncio.gather(*tasks)
        logger.info(f'Channels and Members loaded in {time.time() - start_time} seconds')
        # noinspection PyAsyncCall
        self.bot.loop.create_task(self.manage_servers())
