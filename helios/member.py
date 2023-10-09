import asyncio
import datetime
import json
from typing import TYPE_CHECKING, Dict, Any, Optional

import discord

from .abc import HasFlags
from .exceptions import IdMismatchError
from .voice_template import VoiceTemplate
from .database import MemberModel, update_model_instance, objects, TransactionModel

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .server import Server
    from .member_manager import MemberManager
    from .horses.horse import Horse
    from discord import Guild, Member


class HeliosMember(HasFlags):
    _allowed_flags = [
        'FORBIDDEN'
    ]

    def __init__(self, manager: 'MemberManager', member: 'Member', *, data: MemberModel = None):
        self._id = 0
        self.manager = manager
        self.member = member
        self.templates: list['VoiceTemplate'] = []
        self.flags = []

        self.allow_on_voice = True

        self.max_horses = 8

        self._activity_points = 0
        self._points = 0
        self._ap_paid = 0

        self._last_check = get_floor_now()
        self._partial = 0
        self._changed = False
        self._new = True
        self._db_entry: Optional[MemberModel] = data
        if data:
            self._deserialize(data)

    def __eq__(self, o: Any):
        if isinstance(o, HeliosMember):
            return self.id == o.id
        elif isinstance(o, discord.Member):
            return self.id == o.id and self.guild.id == o.guild.id
        elif o is None:
            return False
        else:
            return NotImplemented

    @property
    def id(self):
        return self.member.id

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
    def verified(self) -> bool:
        role = self.server.verified_role
        if role is None:
            return True
        mem_role = self.member.get_role(role.id)
        return mem_role is not None

    @property
    def horses(self) -> Dict[int, 'Horse']:
        return self.server.stadium.get_owner_horses(self)

    @property
    def points(self) -> int:
        return self._points

    @points.setter
    def points(self, value: int):
        self._changed = True
        if value < 0:
            value = 0
        self._points = value

    @property
    def activity_points(self) -> int:
        return self._activity_points

    def add_activity_points(self, amt: int):
        self._activity_points += amt
        self._changed = True

    def set_activity_points(self, amt: int):
        self._activity_points = amt
        self._changed = True

    def create_template(self):
        template = VoiceTemplate(self, name=self.member.name)
        self.templates.append(template)
        return template

    def _deserialize(self, data: MemberModel):
        if self.member.id != data.member_id:
            raise IdMismatchError('Member Ids do not match.')
        if self.server.id != data.server_id:
            raise IdMismatchError('Server Ids do not match.')

        self._id = data.id
        for temp in json.loads(data.templates):
            template = VoiceTemplate(self, temp['name'], data=temp)
            self.templates.append(template)
        self.flags = json.loads(data.flags)
        self._activity_points = data.activity_points
        self._points = data.points
        self._ap_paid = data.ap_paid
        self._new = False
        self._changed = False

    def serialize(self) -> dict:
        data = {
            'id': self._id,
            'server': self.server.id,
            'member_id': self.member.id,
            'templates': json.dumps([x.serialize() for x in self.templates]),
            'flags': json.dumps(self.flags),
            'activity_points': self._activity_points,
            'points': self._points,
            'ap_paid': self._ap_paid
        }
        if self._id == 0:
            del data['id']
        return data

    def claim_daily(self) -> bool:
        """
        :dep
        :return: Whether the daily could be claimed.
        """
        # stadium = self.server.stadium
        # if self.settings['day_claimed'] != stadium.day:
        #     self.points += stadium.daily_points
        #     self.settings['day_claimed'] = stadium.day
        #     return True
        # else:
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
        if self.member.bot:
            self._changed = False
            return
        if self._new:
            self._db_entry = MemberModel(**self.serialize())
            self._db_entry.save()
            self._new = False
            self._id = self._db_entry.id
            self._changed = False
        if self._changed or force:
            update_model_instance(self._db_entry, self.serialize())
            self._db_entry.save()
            self._changed = False

    async def load(self):
        if self._id != 0:
            self._db_entry = MemberModel.get(id=self._id)
        else:
            self._db_entry = MemberModel.get(server=self.server.id, member_id=self.member.id)
        self._deserialize(self._db_entry)

    async def verify(self):
        role = self.server.verified_role
        if self.member.get_role(role.id):
            return

        await self.member.add_roles(role)

    async def add_points(self, price: int, payee: str, description: str):
        if price == 0:
            return
        self.points += price
        await objects.create(TransactionModel, member=self._db_entry,
                             description=description[:50], amount=price,
                             payee=payee[:25])

    async def payout_activity_points(self):
        points = self._activity_points - self._ap_paid
        if points <= 0:
            return 0
        await self.add_points(points, 'Helios', 'Activity Points Payout')
        self._ap_paid = self._activity_points
        return points

    async def temp_mute(self, duration: int):
        async def unmute(m):
            await asyncio.sleep(duration)
            if await self.temp_unmute():
                await self.bot.event_manager.delete_action(m)

        if self.member.voice:
            await self.member.edit(mute=True)
            self.allow_on_voice = False
            model = await self.bot.event_manager.add_action('on_voice', self, 'unmute')
            self.bot.loop.create_task(unmute(model))
            return True
        return False

    async def temp_unmute(self):
        self.allow_on_voice = True
        if self.member.voice:
            await self.member.edit(mute=False)
            return True
        else:
            return False

    async def get_point_mutes(self) -> int:
        day_ago = discord.utils.utcnow() - datetime.timedelta(days=1)
        last_muted = None
        duration = datetime.timedelta()
        async for audit in self.guild.audit_logs(after=day_ago, oldest_first=True,
                                                 action=discord.AuditLogAction.member_update, user=self.guild.me):
            if audit.target != self.member:
                continue

            try:
                if audit.changes.before.mute is False and audit.changes.after.mute is True:
                    last_muted = audit.created_at

                if audit.changes.before.mute is True and audit.changes.after.mute is False and last_muted is not None:
                    duration += audit.created_at - last_muted
                    last_muted = None
            except AttributeError:
                ...

        return int(duration.total_seconds() // 60)


def get_floor_now() -> datetime.datetime:
    now = datetime.datetime.now().astimezone()
    now = now - datetime.timedelta(
        seconds=now.second,
        microseconds=now.microsecond
    )
    return now
