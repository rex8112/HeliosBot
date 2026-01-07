#  MIT License
#
#  Copyright (c) 2025 Riley Winkler
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

#  MIT License
#
#  Copyright (c) 2025 Riley Winkler
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
from datetime import datetime, timezone
from enum import Enum

from websockets import connect, ConnectionClosed

class Opcode(Enum):
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    RESUME = 6
    HELLO = 10
    HEARTBEAT_ACK = 11

class WebSocketClient:
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.op_listeners = {}
        self.ws = None

        self._last_heartbeat = datetime.now()
        self._last_heartbeat_ack = datetime.now()

        self.op_listeners[Opcode.HEARTBEAT_ACK] = self.heartbeat_ack

    async def connect(self, url: str):
        async with connect(url) as ws:
            self.ws = ws
            try:
                while True:
                    data = await ws.recv()
                    asyncio.create_task(self.recv(data))
            except ConnectionClosed:
                await self.ws.close()
        self.ws = None

    async def heartbeat(self):
        while self.ws is not None:
            await self.send({'op': 1})
            self._last_heartbeat = datetime.now()
            await asyncio.sleep(5)

    async def send(self, data: dict):
        await self.ws.send(data)

    async def recv(self, resp):
        """Handle received data."""
        if 'op' in resp:
            await self.op_listeners[Opcode(resp['op'])](resp)
        pass

    async def heartbeat_ack(self, resp):
        self._last_heartbeat_ack = datetime.now()