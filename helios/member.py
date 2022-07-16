import datetime
from typing import TYPE_CHECKING

from .abc import HasSettings, HasFlags
from .exceptions import IdMismatchError
from .tools.settings import Settings

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .server import Server
    from .member_manager import MemberManager
    from .voice_template import VoiceTemplate
    from discord import Guild, Member


class HeliosMember(HasFlags, HasSettings):
    _default_settings = {
        'activity_points': 0,
        'points': 0
    }
    _allowed_flags = [
        'FORBIDDEN'
    ]

    def __init__(self, manager: 'MemberManager', member: 'Member', *, data: dict = None):
        self._id = 0
        self.manager = manager
        self.member = member
        self.templates: dict[int, 'VoiceTemplate'] = {}
        self.settings = Settings(self._default_settings, bot=self.bot, guild=self.guild)
        self.flags = []

        self._last_check = get_floor_now()
        self._partial = 0
        self._changed = False
        self._new = True
        if data:
            self._deserialize(data)

    @property
    def server(self) -> 'Server':
        return self.manager.server

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
        data = {
            'id': self._id,
            'server': self.server.id,
            'member_id': self.member.id,
            'settings': self.settings.to_dict(),
            'flags': self.flags
        }
        if self._id == 0:
            del data['id']
        return data

    def check_voice(self, amt: int, partial: int = 4) -> bool:
        """
        Check if member is in a non-afk voice channel and apply amt per minute since last check.
        :param amt: Amount to apply per minute of being in a channel.
        :param partial: Amount of times required to get amt if alone.
        :return: Whether the member was given points or partial points.
        """
        now = get_floor_now()
        delta = now - self._last_check
        minutes = delta.seconds // 60
        self._last_check = now

        if self.member.voice and not self.member.voice.afk:
            for _ in range(minutes):
                if len(self.member.voice.channel.members) > 1:
                    self.add_activity_points(amt)
                elif self._partial >= partial:
                    self.add_activity_points(amt)
                    self._partial = 0
                else:
                    self._partial += 1
            return True
        return False

    async def save(self, force=False):
        data = None
        if self._new:
            data = await self.bot.helios_http.post_member(self.serialize())
            self._new = False
        if self._changed or force:
            data = await self.bot.helios_http.patch_member(self.serialize())
        if data:
            self._changed = False
            self._id = data.get('id')

    async def load(self):
        if self._id != 0:
            data = await self.bot.helios_http.get_member(self._id)
        else:
            data = await self.bot.helios_http.get_member(params={'server': self.server.id, 'member_id': self.member.id})
            data = data[0]
        self._deserialize(data)


def get_floor_now() -> datetime.datetime:
    now = datetime.datetime.now().astimezone()
    now = now - datetime.timedelta(
        seconds=now.second,
        microseconds=now.microsecond
    )
    return now
