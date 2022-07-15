from typing import TYPE_CHECKING
from .member import HeliosMember

if TYPE_CHECKING:
    from .server import Server


class MemberManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.members: dict[int, HeliosMember] = {}

    @property
    def bot(self):
        return self.server.bot

    def get(self, member_id: int):
        return self.members.get(member_id)

    async def setup(self, member_data: list[dict] = None):
        ...
