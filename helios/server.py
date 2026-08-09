from typing import TYPE_CHECKING
from discord import Guild

if TYPE_CHECKING:
    from .server_manager import ServerManager

class Server:
    def __init__(self, manager: 'ServerManager', guild: Guild):
        self.manager = manager
        self.guild = guild

    @property
    def id(self) -> int:
        return self.guild.id

    @property
    def bot(self):
        return self.manager.bot