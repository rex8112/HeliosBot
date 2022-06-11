import asyncio

from helios import HeliosBot


class ServerManager:
    def __init__(self, bot: HeliosBot):
        self.bot = bot
        self.servers = {}
        self.queue = asyncio.Queue()
