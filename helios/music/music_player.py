from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..server import Server


class MusicPlayer:
    def __init__(self, server: 'Server'):
        self.server = server
