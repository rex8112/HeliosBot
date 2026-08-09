from .exceptions import DuplicateServerException
from .server import Server

class ServerManager:
    def __init__(self, bot):
        self.bot = bot
        self.servers = {}

    async def get(self, _id: int) -> Server:
        return self.servers.get(_id)

    def _add(self, server: Server):
        """Add a server to the servers dict"""
        if server.id in self.servers:
            raise DuplicateServerException('Server already added')
        self.servers[server.id] = server
        return server

    def _remove(self, server: Server):
        """Remove a server from the servers dict"""
        self.servers.pop(server.id)