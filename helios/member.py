import datetime
from typing import TYPE_CHECKING, Dict

from .abc import HasSettings, HasFlags
from .exceptions import IdMismatchError
from .tools.settings import Settings, Item
from .voice_template import VoiceTemplate

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .server import Server
    from .member_manager import MemberManager
    from .horses.horse import Horse
    from discord import Guild, Member


class HeliosMember(HasFlags, HasSettings):
    _default_settings = {
        'activity_points': 0,
        'points': 0,
        'day_claimed': 0
    }
    _allowed_flags = [
        'FORBIDDEN'
    ]

    def __init__(self, manager: 'MemberManager', member: 'Member', *, data: dict = None):
        self._id = 0
        self.manager = manager
        self.member = member
        self.settings = self._default_settings.copy()
        self.templates: list['VoiceTemplate'] = []
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

    @property
    def horses(self) -> Dict[int, 'Horse']:
        return self.server.stadium.get_owner_horses(self)

    @property
    def points(self) -> int:
        return self.settings['points']

    @points.setter
    def points(self, value: int):
        self._changed = True
        if value < 0:
            value = 0
        self.settings['points'] = int(value)

    @property
    def activity_points(self) -> int:
        return self.settings['activity_points']

    def add_activity_points(self, amt: int):
        self.settings['activity_points'] += amt
        self._changed = True

    def set_activity_points(self, amt: int):
        self.settings.activity_points = amt
        self._changed = True

    def create_template(self):
        template = VoiceTemplate(self, name=self.member.name)
        self.templates.append(template)
        return template

    def _deserialize(self, data: dict):
        if self.member.id != data.get('member_id'):
            raise IdMismatchError('Member Ids do not match.')
        if self.server.id != data.get('server'):
            raise IdMismatchError('Server Ids do not match.')

        self._id = data.get('id')
        for temp in data.get('templates', []):
            template = VoiceTemplate(self, temp['name'], data=temp)
            self.templates.append(template)
        settings = {**self._default_settings, **data.get('settings', {})}
        self.settings = Item.deserialize_dict(settings, bot=self.bot, guild=self.guild)
        self.flags = data.get('flags')
        self._new = False
        self._changed = False

    def serialize(self) -> dict:
        data = {
            'id': self._id,
            'server': self.server.id,
            'member_id': self.member.id,
            'templates': [x.serialize() for x in self.templates],
            'settings': Item.serialize_dict(self.settings),
            'flags': self.flags
        }
        if self._id == 0:
            del data['id']
        return data

    def claim_daily(self) -> bool:
        """
        :return: Whether the daily could be claimed.
        """
        stadium = self.server.stadium
        if self.settings['day_claimed'] != stadium.day:
            self.points += stadium.daily_points
            self.settings['day_claimed'] = stadium.day
            return True
        else:
            return False

    def check_voice(self, amt: int, partial: int = 4) -> bool:
        """
        Check if user is in a non-afk voice channel and apply amt per minute since last check.
        :param amt: Amount to apply per minute of being in a channel.
        :param partial: Amount of times required to get amt if alone.
        :return: Whether the user was given points or partial points.
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
        if self.member.bot:
            self._changed = False
            return
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
