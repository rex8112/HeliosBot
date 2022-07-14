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

    def __init__(self, server: 'Server', member: 'Member'):
        self._id = 0
        self.server = server
        self.member = member
        self.settings = Settings(self._default_settings, bot=self.bot, guild=self.guild)
        self.flags = []

        self._changed = False
        self._new = False

    @property
    def bot(self) -> 'HeliosBot':
        return self.server.bot

    @property
    def guild(self) -> 'Guild':
        return self.server.guild

    def _deserialize(self, data: dict):
        if self.member.id != data.get('member_id'):
            raise IdMismatchError('Member Ids do not match.')
        if self.server.id != data.get('server'):
            raise IdMismatchError('Server Ids do not match.')

        self._id = data.get('id')
        settings = {**self._default_settings, **data.get('settings', {})}
        self.settings = Settings(settings, bot=self.bot, guild=self.guild)
        self.flags = data.get('flags')

    def serializable(self) -> dict:
        return {
            'id': self._id,
            'server': self.server.id,
            'member_id': self.member.id,
            'settings': self.settings.to_dict(),
            'flags': self.flags
        }
