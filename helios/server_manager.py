import asyncio

from .helios_bot import HeliosBot


class ServerManager:
    def __init__(self, bot: HeliosBot):
        self.bot = bot
        self.servers = {}
        self.queue = asyncio.Queue()
