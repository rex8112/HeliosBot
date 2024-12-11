#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import asyncio
import datetime
import json
import re
from typing import TYPE_CHECKING, Any, Optional, Union

import discord
from discord.utils import format_dt

from .abc import HasFlags
from .colour import Colour
from .database import MemberModel, objects, TransactionModel, DailyModel
from .exceptions import IdMismatchError
from .inventory import Inventory
from .items import Items
from .violation import Violation
from .voice_template import VoiceTemplate

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .server import Server
    from .member_manager import MemberManager
    from discord import Guild, Member


def round_down_hundred(x: int) -> int:
    return int(x - x % 100)


class HeliosMember(HasFlags):
    _allowed_flags = [
        'FORBIDDEN'
    ]

    def __init__(self, manager: 'MemberManager', member: 'Member', *, data: MemberModel = None):
        self._id = 0
        self.manager = manager
        self.member = member
        self.templates: list['VoiceTemplate'] = []
        self.inventory: Optional['Inventory'] = None
        self.flags = []

        self._allow_on_voice = 0

        self.max_horses = 8

        self._activity_points = 0
        self._points = 0
        self._ap_paid = 0

        self._point_mutes_cache = (datetime.datetime(year=2000, month=1, day=1,
                                                     tzinfo=datetime.datetime.utcnow().astimezone().tzinfo), 0)

        self._temp_mute_data: Optional[tuple['HeliosMember', int]] = None
        self._temp_deafen_data: Optional[tuple['HeliosMember', int]] = None
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

    def __hash__(self):
        return self.member.__hash__()

    def __str__(self):
        return self.member.display_name

    @property
    def id(self):
        return self.member.id

    @property
    def db_id(self):
        return self._db_entry.id

    @property
    def json_identifier(self):
        return f'HM.{self.id}.{self.server.id}'

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
        return self.member in role.members

    @property
    def points(self) -> int:
        return self._points

    @points.setter
    def points(self, value: int):
        self._changed = True
        # if value < 0:
        #     value = 0
        self._points = value

    @property
    def activity_points(self) -> int:
        return self._activity_points

    @property
    def unpaid_ap(self):
        return int(self._activity_points - self._ap_paid)

    @property
    def allow_on_voice(self) -> bool:
        return self._allow_on_voice == 0

    @allow_on_voice.setter
    def allow_on_voice(self, value: bool):
        if value is True and self._allow_on_voice > 0:
            self._allow_on_voice -= 1
        else:
            self._allow_on_voice += 1

    @property
    def db_entry(self) -> MemberModel:
        return self._db_entry

    @property
    def effects(self):
        return self.bot.effects.get_effects(self)

    def has_effect(self, effect: str):
        effects = self.effects
        for e in effects:
            if e.type.lower() == effect.lower():
                return True
        return False

    def add_activity_points(self, amt: int):
        self._activity_points += amt
        self._changed = True

    def set_activity_points(self, amt: int):
        self._activity_points = amt
        self._changed = True

    def get_template(self, name: str):
        for template in self.templates:
            if template.name.lower() == name.lower():
                return template
        return None

    def create_template(self):
        name = self.member.name
        exists = True
        counter = 1
        while exists:
            temp = self.get_template(name)
            if temp is None:
                exists = False
            else:
                name = f'{self.member.name} ({counter})'
                counter += 1

        template = VoiceTemplate(self, name=name)
        self.templates.append(template)
        return template

    def is_noob(self):
        return self.activity_points < 1440

    def is_shielded(self):
        if self.member.voice is not None:
            channel = self.member.voice.channel
            if channel is not None:
                channel = self.server.channels.dynamic_voice.channels.get(channel.id)
                if channel is not None and channel.has_effect('channelshieldeffect'):
                    return True
        return self.has_effect('shieldeffect')

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

    def get_game_activity(self):
        for activity in self.member.activities:
            if (not isinstance(activity, discord.CustomActivity) and activity.name != 'Hang Status'
                    and activity.type == discord.ActivityType.playing):
                return activity

    # noinspection PyUnresolvedReferences
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
            'member_id': self.member.id,
            'templates': json.dumps([x.serialize() for x in self.templates]),
            'flags': json.dumps(self.flags),
            'activity_points': self._activity_points,
            'points': self._points,
            'ap_paid': self._ap_paid
        }
        return data

    def point_to_activity_percentage(self) -> float:
        if self.activity_points == 0:
            return 0.0
        return self.points / self.activity_points

    def daily_points(self) -> int:
        return 7_500

    async def load_inventory(self):
        self.inventory = await Inventory.load(self)

    async def claim_daily(self) -> int:
        """
        :return: Whether the daily could be claimed.
        """
        days = get_day()
        points = self.daily_points()
        if points == 0:
            return 0
        give = await DailyModel.claim(self._db_entry, days)
        if give:
            item = Items.gamble_credit(int(points / 5))
            await self.inventory.add_item(item, 5)
            return points
        return 0

    async def is_daily_claimed(self, *, offset: int = 0) -> bool:
        days = get_day() + offset
        return await DailyModel.is_claimed(self._db_entry, days)

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
            data = self.serialize()
            self._db_entry = await MemberModel.create_model(self.server.db_entry, **data)
            self._new = False
            self._id = self._db_entry.id
            self._changed = False
        if self._changed or force:
            data = self.serialize()
            self._db_entry.update_model_instance(self._db_entry, data)
            await self._db_entry.async_save()
            self._changed = False
        await self.inventory.save()

    async def load(self):
        if self._id != 0:
            self._db_entry = MemberModel.get(id=self._id)
        else:
            self._db_entry = MemberModel.get(server=self.server.id, member_id=self.member.id)
        self._deserialize(self._db_entry)

    async def verify(self, announce=True):
        role = self.server.verified_role
        if self.member.get_role(role.id):
            return

        embed = discord.Embed(
            title='Verified!',
            description='You have been verified!\nIf you are in a voice channel, you may need to rejoin to be able to '
                        'speak.',
            colour=discord.Colour.green()
        )
        await self.member.add_roles(role)
        if announce:
            await self.member.send(embed=embed)

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

    async def clear_on_voice(self,  action: str):
        actions = await self.bot.event_manager.get_specific_actions('on_voice', self, action)
        [await self.bot.event_manager.delete_action(x) for x in actions]

    async def voice_mute(self, *, reason=None):
        await self.clear_on_voice('unmute')
        voice = self.member.voice
        if voice is None or voice.channel is None:
            await self.bot.event_manager.add_action('on_voice', self, 'mute')
            return True
        elif self.member.voice.mute is False:
            try:
                await self.member.edit(mute=True, reason=reason)
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

    async def voice_unmute(self, *, reason=None):
        await self.clear_on_voice('mute')
        voice = self.member.voice
        if voice is None or voice.channel is None:
            await self.bot.event_manager.add_action('on_voice', self, 'unmute')
            return True
        elif self.member.voice.mute is True:
            try:
                await self.member.edit(mute=False, reason=reason)
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

    async def voice_deafen(self, *, reason=None):
        await self.clear_on_voice('undeafen')
        voice = self.member.voice
        if voice is None or voice.channel is None:
            await self.bot.event_manager.add_action('on_voice', self, 'deafen')
            return True
        elif self.member.voice.deaf is False:
            try:
                await self.member.edit(deafen=True, reason=reason)
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

    async def voice_undeafen(self, *, reason=None):
        await self.clear_on_voice('deafen')
        voice = self.member.voice
        if voice is None or voice.channel is None:
            await self.bot.event_manager.add_action('on_voice', self, 'undeafen')
            return True
        elif self.member.voice.deaf is True:
            try:
                await self.member.edit(deafen=False, reason=reason)
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

    async def voice_mute_deafen(self, *, reason=None):
        await self.clear_on_voice('undeafen')
        await self.clear_on_voice('unmute')
        voice = self.member.voice
        if voice is None or voice.channel is None:
            await self.bot.event_manager.add_action('on_voice', self, 'mute')
            await self.bot.event_manager.add_action('on_voice', self, 'deafen')
            return True
        elif self.member.voice.mute is False or self.member.voice.deaf is False:
            try:
                await self.member.edit(mute=True, deafen=True, reason=reason)
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

    async def voice_unmute_undeafen(self, *, reason=None):
        await self.clear_on_voice('deafen')
        await self.clear_on_voice('mute')
        voice = self.member.voice
        if voice is None or voice.channel is None:
            await self.bot.event_manager.add_action('on_voice', self, 'unmute')
            await self.bot.event_manager.add_action('on_voice', self, 'undeafen')
        elif self.member.voice.mute is True or self.member.voice.deaf is True:
            try:
                await self.member.edit(mute=False, deafen=False, reason=reason)
                return True
            except (discord.Forbidden, discord.HTTPException):
                return False

    async def temp_mute(self, duration: int, muter: 'HeliosMember', price: int):
        async def unmute(m):
            await asyncio.sleep(duration)
            if await self.temp_unmute(duration):
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

    async def temp_unmute(self, duration: int = 90):
        self.allow_on_voice = True
        muter, cost = self._temp_mute_data  # type: HeliosMember, int
        self._temp_mute_data = None
        if self.member.voice:
            if self.member.voice.mute is False:
                unmuter = await self.who_unmuted(duration)
                hel = self.server.me
                if unmuter and unmuter != muter.member and unmuter != hel.member:
                    member = self.server.members.get(unmuter.id)
                    v = Violation.new_shop(member, hel, cost,
                                           f'Unmuting {self.member.name} during a temporary mute.')
                    await self.server.court.new_violation(v)
                    embed = discord.Embed(
                        title='Notice of Refund',
                        colour=discord.Colour.green(),
                        description='Due to unexpected interference, your last Shop purchase was invalidated and you '
                                    f'have been refunded **{cost}** {self.server.points_name.capitalize()}.'
                    )
                    await muter.add_points(cost, 'Helios', 'Helios Shop Refund: Temp Mute')
                    await muter.member.send(embed=embed)

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

    async def who_unmuted(self, duration: int = 90) -> Optional[Union[discord.Member, discord.User]]:
        after = discord.utils.utcnow() - datetime.timedelta(seconds=duration)
        async for audit in self.guild.audit_logs(action=discord.AuditLogAction.member_update, after=after,
                                                 oldest_first=False):
            if audit.target != self.member:
                continue
            try:
                if audit.changes.before.mute is True and audit.changes.after.mute is False:
                    return audit.user
            except AttributeError:
                continue
        return None

    async def temp_deafen(self, duration: int, deafener: 'HeliosMember', price: int):
        async def undeafen(m):
            await asyncio.sleep(duration)
            if await self.temp_undeafen(duration):
                await self.bot.event_manager.delete_action(m)
            embed = discord.Embed(
                title='Deafened',
                colour=discord.Colour.orange(),
                description=f'Someone spent **{price}** {self.server.points_name.capitalize()} to deafen you for '
                            f'**{duration}** seconds.'
            )
            await self.member.send(embed=embed)

        if self.member.voice:
            try:
                await self.member.edit(deafen=True, reason=f'{deafener.member.name} temp deafened for {duration} seconds')
            except discord.Forbidden:
                return False
            self._temp_deafen_data = (deafener, price)
            self.allow_on_voice = False
            model = await self.bot.event_manager.add_action('on_voice', self, 'undeafen')
            self.bot.loop.create_task(undeafen(model))
            return True
        return False

    async def temp_undeafen(self, duration: int = 90):
        self.allow_on_voice = True
        muter, cost = self._temp_deafen_data  # type: HeliosMember, int
        self._temp_deafen_data = None
        if self.member.voice:
            if self.member.voice.mute is False:
                unmuter = await self.who_undeafened(duration)
                hel = self.server.me
                if unmuter and unmuter != muter.member and unmuter != hel.member:
                    member = self.server.members.get(unmuter.id)
                    v = Violation.new_shop(member, hel, cost,
                                           f'Undeafening {self.member.name} during a temporary deafen.')
                    await self.server.court.new_violation(v)
                    embed = discord.Embed(
                        title='Notice of Refund',
                        colour=discord.Colour.green(),
                        description='Due to unexpected interference, your last Shop purchase was invalidated and you '
                                    f'have been refunded **{cost}** {self.server.points_name.capitalize()}.'
                    )
                    await muter.add_points(cost, 'Helios', 'Helios Shop Refund: Temp Deafen')
                    await muter.member.send(embed=embed)

            await self.member.edit(deafen=False)
            return True
        else:
            return False

    async def who_undeafened(self, duration: int = 90) -> Optional[Union[discord.Member, discord.User]]:
        after = discord.utils.utcnow() - datetime.timedelta(seconds=duration)
        async for audit in self.guild.audit_logs(action=discord.AuditLogAction.member_update, after=after,
                                                 oldest_first=False):
            if audit.target != self.member:
                continue
            try:
                if audit.changes.before.deaf is True and audit.changes.after.deaf is False:
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

    async def get_point_deafen_duration(self, force=False) -> int:
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
                if audit.changes.before.deaf is False and audit.changes.after.deaf is True:
                    if not audit.reason:
                        continue
                    regex = r'deafened for (\d{1,2}) seconds'
                    groups = re.search(regex, audit.reason).groups()
                    if len(groups) == 1:
                        seconds += int(groups[0])
            except AttributeError:
                ...

        self._point_mutes_cache = (datetime.datetime.now().astimezone(), int(seconds))
        return int(seconds)

    async def get_24hr_change(self):
        res = await TransactionModel.get_24hr_change(self)
        return res if res else 0

    async def get_24hr_transfer(self):
        res = await TransactionModel.get_24hr_transfers_out(self)
        return res if res else 0


def get_floor_now() -> datetime.datetime:
    now = datetime.datetime.now().astimezone()
    now = now - datetime.timedelta(
        seconds=now.second,
        microseconds=now.microsecond
    )
    return now


def get_day() -> int:
    tz = datetime.datetime.now().astimezone().tzinfo
    epoch = datetime.datetime(2024, 7, 1, tzinfo=tz)
    now = datetime.datetime.now().astimezone()
    now = now - epoch
    return int(now.total_seconds() // 86_400)
