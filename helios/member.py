from typing import TYPE_CHECKING

from .abc import HasSettings, HasFlags
from .exceptions import IdMismatchError
from .tools.settings import Settings

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .server import Server
    from discord import Guild, Member


class HeliosMember(HasFlags, HasSettings):
    _default_settings = {
        'activity_points': 0,
        'points': 0
    }
    _allowed_flags = [
        'FORBIDDEN'
    ]

    def __init__(self, server: 'Server', member: 'Member', *, data: dict = None):
        self._id = 0
        self.server = server
        self.member = member
        self.settings = Settings(self._default_settings, bot=self.bot, guild=self.guild)
        self.flags = []

        self._changed = False
        self._new = True
        if data:
            self._deserialize(data)

    @property
    def bot(self) -> 'HeliosBot':
        return self.server.bot

    @property
    def guild(self) -> 'Guild':
        return self.server.guild

    def add_activity_points(self, amt: int):
        self.settings.activity_points += amt
        self._changed = True

    def set_activity_points(self, amt: int):
        self.settings.activity_points = amt
        self._changed = True

    def _deserialize(self, data: dict):
        if self.member.id != data.get('member_id'):
            raise IdMismatchError('Member Ids do not match.')
        if self.server.id != data.get('server'):
            raise IdMismatchError('Server Ids do not match.')

        self._id = data.get('id')
        settings = {**self._default_settings, **data.get('settings', {})}
        self.settings = Settings(settings, bot=self.bot, guild=self.guild)
        self.flags = data.get('flags')
        self._new = False
        self._changed = False

    def serialize(self) -> dict:
        return {
            'id': self._id,
            'server': self.server.id,
            'member_id': self.member.id,
            'settings': self.settings.to_dict(),
            'flags': self.flags
        }

    async def save(self, force=False):
        data = None
        if self._new:
            data = await self.bot.helios_http.post_member(self.serialize())
        if self._changed or force:
            data = await self.bot.helios_http.patch_member(self.serialize())
        if data:
            self._changed = False
            self._id = data.get('id')

    async def load(self):
        data = await self.bot.helios_http.get_member(self._id)
        self._deserialize(data)

