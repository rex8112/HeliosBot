#  MIT License
#
#  Copyright (c) 2026 Riley Winkler
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