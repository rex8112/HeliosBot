import asyncio
import datetime
import json
import re
from typing import TYPE_CHECKING, Dict, Any, Optional, Union

import discord
from discord.utils import format_dt

from .abc import HasFlags
from .colour import Colour
from .exceptions import IdMismatchError
from .violation import Violation
from .voice_template import VoiceTemplate
from .database import MemberModel, objects, TransactionModel

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

        self._point_mutes_cache = (datetime.datetime(year=2000, month=1, day=1,
                                                     tzinfo=datetime.datetime.utcnow().astimezone().tzinfo), 0)

        self._temp_mute_data: Optional[tuple['HeliosMember', int]] = None
        self._last_check = get_floor_now()
        self._partial = 0
        self._changed = False
        self._new = True
        self._db_entry: Optional[MemberModel] = data
        if data:
            self._deserialize(data)

    def __eq__(self, o: Any):
        if isinstance(o, HeliosMember):
            return self.db_id == o.db_id
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
    def db_id(self):
        return self._db_entry.id

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

    @property
    def unpaid_ap(self):
        return int(self._activity_points - self._ap_paid)

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

    def is_noob(self):
        return self.activity_points < 1440

    def profile(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.member.display_name,
            colour=self.colour(),
            description=self.member.name
        )
        embed.set_thumbnail(url=self.member.display_avatar.url)
        embed.add_field(name=f'{self.server.points_name.capitalize()}', value=f'{self.points:,}')
        embed.add_field(name=f'Activity {self.server.points_name.capitalize()}', value=f'{self.activity_points:,}')
        embed.add_field(name=f'Joined {self.server.guild.name}', value=format_dt(self.member.joined_at, 'R'))
        return embed

    def colour(self):
        colour = discord.Colour.default()
        for role in reversed(self.member.roles):
            if role.colour != discord.Colour.default():
                if (self.server.guild.premium_subscriber_role
                        and role.colour == self.server.guild.premium_subscriber_role.colour):
                    continue
                return role.colour
        return colour

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

    async def check_voice(self, amt: int, partial: int = 4) -> bool:
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
            before = self.is_noob()
            for _ in range(minutes):
                if len(self.member.voice.channel.members) > 1:
                    self.add_activity_points(amt)
                elif self._partial >= partial:
                    self.add_activity_points(amt)
                    self._partial = 0
                else:
                    self._partial += 1
            if before is True and self.is_noob() is False:
                embed = discord.Embed(
                    title='Congratulations!',
                    colour=Colour.success(),
                    description='You have graduated from noob status! All restrictions have been lifted.'
                )
                try:
                    await self.member.send(embed=embed)
                except (discord.Forbidden, discord.NotFound):
                    ...
            return True
        return False

    async def save(self, force=False):
        if self._new:
            self._db_entry = MemberModel(**self.serialize())
            await self._db_entry.async_save()
            self._new = False
            self._id = self._db_entry.id
            self._changed = False
        if self._changed or force:
            self._db_entry.update_model_instance(self._db_entry, self.serialize())
            await self._db_entry.async_save()
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
        if len(description) > 50:
            description = description[:47] + '...'
        self.points += price
        await objects.create(TransactionModel, member=self._db_entry,
                             description=description, amount=price,
                             payee=payee[:25])

    async def transfer_points(self, target: 'HeliosMember', price: int, description: str,
                              receive_description: str = None):
        await target.add_points(price, self.member.name, receive_description if receive_description else description)
        await self.add_points(-price, target.member.name, description)

    async def payout_activity_points(self):
        points = self._activity_points - self._ap_paid
        if points <= 0:
            return 0
        await self.add_points(points, 'Helios', 'Activity Points Payout')
        self._ap_paid = self._activity_points
        return points

    async def temp_mute(self, duration: int, muter: 'HeliosMember', price: int):
        async def unmute(m):
            await asyncio.sleep(duration)
            if await self.temp_unmute():
                await self.bot.event_manager.delete_action(m)

        if self.member.voice:
            try:
                embed = discord.Embed(
                    title='Muted',
                    colour=discord.Colour.orange(),
                    description=f'Someone spent **{price}** {self.server.points_name.capitalize()} to mute you for '
                                f'**{duration}** seconds.'
                )

                await self.member.edit(mute=True, reason=f'{muter.member.name} temp muted for {duration} seconds')

                await self.member.send(embed=embed)
            except discord.Forbidden:
                return False
            self._temp_mute_data = (muter, price)
            self.allow_on_voice = False
            model = await self.bot.event_manager.add_action('on_voice', self, 'unmute')
            self.bot.loop.create_task(unmute(model))
            return True
        return False

    async def temp_unmute(self):
        self.allow_on_voice = True
        muter, cost = self._temp_mute_data
        self._temp_mute_data = None
        if self.member.voice:
            if self.member.voice.mute is False:
                unmuter = await self.who_unmuted()
                if unmuter and unmuter != muter.member:
                    member = self.server.members.get(unmuter.id)
                    v = Violation.new_shop(member, muter, cost,
                                           f'Unmuting {self.member.name} during a temporary mute.')
                    await self.server.court.new_violation(v)
            embed = discord.Embed(
                title='Unmuted',
                colour=discord.Colour.green(),
                description=f'You have been unmuted.'
            )

            await self.member.edit(mute=False)

            try:
                await self.member.send(embed=embed)
            except discord.Forbidden:
                ...
            return True
        else:
            return False

    async def who_unmuted(self) -> Optional[Union[discord.Member, discord.User]]:
        async for audit in self.guild.audit_logs(action=discord.AuditLogAction.member_update):
            if audit.target != self.member:
                continue
            try:
                if audit.changes.before.mute is True and audit.changes.after.mute is False:
                    return audit.user
            except AttributeError:
                continue
        return None

    async def get_point_mute_duration(self, force=False) -> int:
        ago = datetime.datetime.now().astimezone() - datetime.timedelta(seconds=15)
        if force is False and self._point_mutes_cache[0] > ago:
            return self._point_mutes_cache[1]
        day_ago = discord.utils.utcnow() - datetime.timedelta(hours=12)
        seconds = 0
        async for audit in self.guild.audit_logs(after=day_ago, oldest_first=True, limit=None,
                                                 action=discord.AuditLogAction.member_update):
            if audit.target != self.member:
                continue

            try:
                if audit.changes.before.mute is False and audit.changes.after.mute is True:
                    if not audit.reason:
                        continue
                    regex = r'muted for (\d{1,2}) seconds'
                    groups = re.search(regex, audit.reason).groups()
                    if len(groups) == 1:
                        seconds += int(groups[0])
            except AttributeError:
                ...

        self._point_mutes_cache = (datetime.datetime.now().astimezone(), int(seconds))
        return int(seconds)


def get_floor_now() -> datetime.datetime:
    now = datetime.datetime.now().astimezone()
    now = now - datetime.timedelta(
        seconds=now.second,
        microseconds=now.microsecond
    )
    return now
