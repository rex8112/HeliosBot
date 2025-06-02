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
from typing import TYPE_CHECKING, Optional, Any

import discord.utils
import peewee_async
from peewee import *

from .tools.config import Config

if TYPE_CHECKING:
    from .member import HeliosMember

settings = Config.from_file_path()

db = peewee_async.MySQLDatabase(settings.db_path, user=settings.db_username, password=settings.db_password,
                                host=settings.db_host, port=int(settings.db_port), charset='utf8mb4')
db.set_allow_sync(False)
objects = peewee_async.Manager(db)


def initialize_db():
    with db.allow_sync():
        db.connect()
        db.create_tables([ServerModel, MemberModel, ChannelModel, TransactionModel,
                          EventModel, ViolationModel, DynamicVoiceModel, DynamicVoiceGroupModel, TopicModel,
                          EffectModel, ThemeModel, BlackjackModel, DailyModel, GameModel, GameAliasModel, PugModel,
                          InventoryModel, StoreModel, TopicSubscriptionModel, StatisticModel, StatisticHistoryModel])


def get_aware_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class JSONField(Field):
    field_type = 'text'

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        return json.loads(value)


class DatetimeTzField(Field):
    field_type = 'DATETIME'

    def db_value(self, value: datetime.datetime) -> str:
        if value:
            return value.strftime('%Y-%m-%d %H:%M:%S')

    def python_value(self, value: datetime.datetime) -> datetime.datetime:
        if value:
            return value.replace(tzinfo=datetime.timezone.utc)


class BaseModel(Model):
    @staticmethod
    def update_model_instance(model: Model, data: dict):
        """Update a model instance with a dictionary."""
        for key, value in data.items():
            old = getattr(model, key)
            if old != value:
                setattr(model, key, value)

    def async_save(self, only=None):
        """Save the model instance asynchronously."""
        return objects.update(self, only=only)

    def async_update(self, **kwargs):
        """Update the model instance asynchronously."""
        self.update_model_instance(self, kwargs)
        return self.async_save(only=kwargs.keys())

    def async_delete(self):
        """Delete the model instance asynchronously."""
        return objects.delete(self)

    class Meta:
        database = db


class VersionModel(BaseModel):
    version = CharField(max_length=12)

    class Meta:
        table_name = 'version'


class ServerModel(BaseModel):
    id = BigIntegerField(primary_key=True, unique=True)
    name = CharField(max_length=26)
    settings = TextField(default="")
    flags = TextField(default="[]")

    class Meta:
        table_name = 'servers'


class ChannelModel(BaseModel):
    id = BigIntegerField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='channels')
    type = CharField(max_length=26)
    settings = TextField(default='')
    flags = TextField(default='[]')

    class Meta:
        table_name = 'channels'


class MemberModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='members')
    member_id = BigIntegerField()
    activity_points = IntegerField(default=0)
    points = IntegerField(default=0)
    ap_paid = IntegerField(default=0)
    templates = TextField(default='[]')
    flags = TextField(default='[]')

    class Meta:
        table_name = 'members'

    @staticmethod
    async def create_model(server: ServerModel, **kwargs):
        """Create a new model instance in the database."""
        return await objects.create(MemberModel, server=server, **kwargs)


class TransactionModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    member = ForeignKeyField(MemberModel, backref='transactions')
    payee = CharField(max_length=25)
    description = CharField(max_length=50)
    amount = IntegerField()
    created_on = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'transactions'

    @staticmethod
    async def get_transactions_paginated(member: 'HeliosMember', page: int, limit: int) -> list['TransactionModel']:
        q = (TransactionModel.select().where(TransactionModel.member_id == member.db_id)
             .order_by(TransactionModel.id.desc()).paginate(page, limit))
        return await objects.prefetch(q)

    @staticmethod
    async def get_24hr_change(member: 'HeliosMember'):
        ago = discord.utils.utcnow() - datetime.timedelta(days=1)
        q = (TransactionModel.select(fn.SUM(TransactionModel.amount).alias('day_change'))
             .where(TransactionModel.member == member.db_entry, TransactionModel.created_on > ago))
        res = await objects.prefetch(q)
        return res[0].day_change

    @staticmethod
    async def get_24hr_transfers_out(member: 'HeliosMember'):
        ago = discord.utils.utcnow() - datetime.timedelta(days=1)
        q = (TransactionModel.select(fn.SUM(TransactionModel.amount).alias('day_transfer'))
             .where(TransactionModel.member == member.db_entry,
                    TransactionModel.created_on > ago,
                    TransactionModel.amount < 0,
                    TransactionModel.description == 'Transferred Points'))
        res = await objects.prefetch(q)
        return int(res[0].day_transfer) if res[0].day_transfer else 0


class EventModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    trigger = CharField(max_length=20)
    action = CharField(max_length=25)
    server_id = ForeignKeyField(ServerModel, backref='startups', null=True)
    target_id = BigIntegerField()

    class Meta:
        table_name = 'events'


class AuditLogModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    action = CharField(max_length=25)
    user = ForeignKeyField(MemberModel, backref='audits')
    target = ForeignKeyField(MemberModel, backref='audits_target')
    description = CharField(max_length=50, null=True)
    created = DatetimeTzField(default=datetime.datetime.now)

    @staticmethod
    async def get_target_temp_mutes(target_id: int) -> list['AuditLogModel']:
        q = AuditLogModel.select().where(AuditLogModel.target_id == target_id, AuditLogModel.action == 'temp_mute')
        audits = await objects.prefetch(q)
        return list(audits)

    class Meta:
        table_name = 'auditlogs'


class ViolationModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='violations')
    user = ForeignKeyField(MemberModel, backref='violations')
    victim = ForeignKeyField(MemberModel, backref='violations_victim', null=True)
    type = IntegerField()
    state = IntegerField()
    cost = IntegerField()
    description = TextField()
    due_date = DatetimeTzField()
    created_on = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'violations'

    @staticmethod
    async def get_violation(violation_id: int, /):
        q = ViolationModel.select().where(ViolationModel.id == violation_id)
        res = await objects.prefetch(q, MemberModel.select())
        return [x for x in res][0] if res else None

    @staticmethod
    async def get_violations(member: 'HeliosMember'):
        q = ViolationModel.select().where(ViolationModel.user_id == member.db_id).order_by(ViolationModel.id.desc())
        return await objects.prefetch(q, MemberModel.select())


class CourtModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    type = IntegerField()
    date = DatetimeTzField()
    judge = ForeignKeyField(MemberModel, backref='judges')
    decision = BooleanField(null=True)
    jury = JSONField(default=[])

    class Meta:
        table_name = 'courts'


class CaseModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    plaintiff = ForeignKeyField(MemberModel, backref='plaintiff_cases')
    defendant = ForeignKeyField(MemberModel, backref='defendant_cases')
    court = ForeignKeyField(CourtModel, backref='cases')
    punishment = JSONField(default={})
    punished = BooleanField(default=False)
    finished = DatetimeTzField(null=True)
    created = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'cases'


class DynamicVoiceGroupModel(BaseModel):
    """A model for dynamic voice groups."""
    id = AutoField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='voice_groups')
    min = IntegerField()
    min_empty = IntegerField(default=1)
    max = IntegerField(default=0)
    template = CharField(max_length=25)
    game_template = CharField(max_length=25)

    class Meta:
        table_name = 'dynamicvoicegroups'

    @staticmethod
    async def get_all(server: ServerModel) -> list['DynamicVoiceGroupModel']:
        """Get all models for a server."""
        q = DynamicVoiceGroupModel.select().where(DynamicVoiceGroupModel.server == server)
        return await objects.prefetch(q)

    @staticmethod
    async def create_model(server: ServerModel, **kwargs):
        """Create a new model instance in the database."""
        return await objects.create(DynamicVoiceGroupModel, server=server, **kwargs)


class DynamicVoiceModel(BaseModel):
    """A model for dynamic voice channels."""
    channel = BigIntegerField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='dynamic_voices')
    settings = JSONField(default={})

    class Meta:
        table_name = 'dynamicvoices'

    @staticmethod
    async def get_all(server: ServerModel) -> list['DynamicVoiceModel']:
        """Get all models for a server."""
        q = DynamicVoiceModel.select().where(DynamicVoiceModel.server == server)
        return await objects.prefetch(q)

    @staticmethod
    async def get_by_channel(channel: int) -> 'DynamicVoiceModel':
        """Get a model by channel ID."""
        return await objects.get(DynamicVoiceModel, channel=channel)

    @staticmethod
    async def create_model(server: ServerModel, **kwargs):
        """Create a new model instance in the database."""
        return await objects.create(DynamicVoiceModel, server=server, **kwargs)


class TopicModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    channel_id = BigIntegerField(unique=True)
    server = ForeignKeyField(ServerModel, backref='topics')
    points = IntegerField()
    state = IntegerField()
    creator = ForeignKeyField(MemberModel, backref='topics', null=True)
    archive_message = BigIntegerField(null=True)
    archive_date = DatetimeTzField(null=True)
    created = DatetimeTzField(default=get_aware_utc_now)
    updated = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'topics'

    def async_save(self, only=None):
        self.updated = get_aware_utc_now()
        return super().async_save(only=only)

    @staticmethod
    def async_create(channel_id: int, server: ServerModel, creator: MemberModel, points: int, state: int):
        return objects.create(TopicModel, channel_id=channel_id, server=server, creator=creator, points=points,
                              state=state)

    @staticmethod
    async def get_by_channel(channel_id: int) -> 'TopicModel':
        q = TopicModel.select().where(TopicModel.channel_id == channel_id)
        return await objects.prefetch(q, MemberModel.select(), ServerModel.select())

    @staticmethod
    async def get_all(server: ServerModel) -> list['TopicModel']:
        q = TopicModel.select().where(TopicModel.server == server)
        return await objects.prefetch(q, MemberModel.select(), ServerModel.select())


class EffectModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    type = CharField(30)
    target = CharField(80)
    duration = IntegerField()
    applied = BooleanField()
    applied_at = DatetimeTzField()
    extra = JSONField(default=dict())

    class Meta:
        table_name = 'effects'

    @classmethod
    async def new(cls, type: str, target: str, duration: int,
                  applied: bool, applied_at: datetime, extra: dict = None):
        if extra is None:
            extra = dict()
        return await objects.create(cls, type=type, target=target, duration=duration, applied=applied,
                                    applied_at=applied_at, extra=extra)

    @classmethod
    async def get_all(cls) -> list['EffectModel']:
        q = cls.select()
        return await objects.prefetch(q)


class ThemeModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='themes')
    name = CharField(max_length=25, unique=True)
    roles = JSONField(default=[])
    groups = JSONField(default=[])
    owner = ForeignKeyField(MemberModel, backref='themes', null=True)
    editable = BooleanField(default=True)
    current = BooleanField(default=False)
    sort_stat = CharField(max_length=25, default='points')
    sort_type = CharField(max_length=25, default='total')
    banner_url = CharField(max_length=255, null=True)
    created = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'themes'

    @classmethod
    async def get_all(cls, server: ServerModel) -> list['ThemeModel']:
        q = cls.select().where(cls.server == server)
        return await objects.prefetch(q)

    @classmethod
    async def get_current(cls, server: ServerModel) -> Optional['ThemeModel']:
        try:
            return await objects.get(ThemeModel, server=server, current=True)
        except DoesNotExist:
            return None

    @classmethod
    async def get_themes(cls, server: ServerModel, owner: MemberModel = None):
        """Get all themes for a server, optionally filtered by owner."""
        if owner:
            q = cls.select().where(cls.server == server, cls.owner == owner)
        else:
            q = cls.select().where(cls.server == server)
        return await objects.prefetch(q)

    @classmethod
    async def get(cls, id: int) -> Optional['ThemeModel']:
        try:
            return await objects.get(ThemeModel, id=id)
        except DoesNotExist:
            return None

    @classmethod
    async def create(cls, server: ServerModel, owner: MemberModel, name: str, roles: list[dict], groups: list[dict]) -> 'ThemeModel':
        return await objects.create(cls, server=server, owner=owner, name=name, roles=roles, groups=groups)


class BlackjackModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    players = JSONField(default=[])
    hands = JSONField(default=[])
    bets = JSONField(default=[])
    powerups = JSONField(default=[])
    winnings = JSONField(default=[])
    dealer_hand = JSONField(default=[])
    created = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'blackjack'

    @classmethod
    async def create(cls, players: list) -> 'BlackjackModel':
        return await objects.create(cls, players=players)


class DailyModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    member = ForeignKeyField(MemberModel, backref='dailies')
    claimed = IntegerField(default=-1)

    class Meta:
        table_name = 'dailies'

    @classmethod
    async def claim(cls, member: MemberModel, day: int):
        try:
            daily = await objects.get(cls, member=member)
            if daily.claimed != day:
                daily.claimed = day
                await daily.async_save()
                return True
            return False
        except DoesNotExist:
            await objects.create(cls, member=member, claimed=day)
            return True

    @classmethod
    async def is_claimed(cls, member: MemberModel, day: int):
        try:
            daily = await objects.get(cls, member=member)
            return daily.claimed == day
        except DoesNotExist:
            return False


class GameModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    name = CharField(max_length=52, unique=True)
    display_name = CharField(max_length=52)
    icon = CharField(max_length=255)
    play_time = IntegerField(default=0)
    last_day_playtime = IntegerField(default=0)
    last_played = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'games'

    @classmethod
    async def create_game(cls, name: str, display_name: str, icon: str) -> 'GameModel':
        return await objects.create(cls, name=name, display_name=display_name, icon=icon)

    async def delete_game(self):
        return await self.async_delete()

    @classmethod
    async def find_game(cls, name: str) -> Optional['GameModel']:
        """Find a game by name or alias."""
        q = cls.select().join(GameAliasModel, join_type=JOIN.LEFT_OUTER).where((cls.name == name) | (GameAliasModel.alias == name))
        try:
            res = await objects.prefetch(q, GameAliasModel.select())
            if res:
                return res[0]
            return None
        except DoesNotExist:
            return None

    @classmethod
    async def set_day_playtime(cls):
        """Set the last day playtime to the current playtime."""
        q = cls.select().where(cls.play_time > cls.last_day_playtime)
        games = await objects.execute(q)
        async with objects.atomic():
            for game in games:
                await game.async_update(last_day_playtime=game.play_time)

    async def add_playtime(self, time: int):
        """Add playtime to the game."""
        self.play_time += time
        self.last_played = get_aware_utc_now()
        return await self.async_save(only=('play_time', 'last_played'))

    async def add_alias(self, alias: str):
        """Add an alias to the game."""
        return await objects.create(GameAliasModel, game=self, alias=alias)

    async def remove_alias(self, alias: str):
        """Remove an alias from the game."""
        q = GameAliasModel.delete().where(GameAliasModel.game == self, GameAliasModel.alias == alias)
        return await objects.execute(q)


class GameAliasModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    game = ForeignKeyField(GameModel, backref='aliases', on_delete='CASCADE')
    alias = CharField(max_length=52, unique=True)

    class Meta:
        table_name = 'game_aliases'


class Lottery(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    game_type = CharField(max_length=16)
    pool = IntegerField()
    frequency = IntegerField()
    numbers = IntegerField()
    range = IntegerField()
    next_game = DatetimeTzField()
    tickets = JSONField(default=[])

    class Meta:
        table_name = 'lotteries'


class PugModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='pugs')
    channel = ForeignKeyField(DynamicVoiceModel, backref='pugs', unique=True)
    server_members = JSONField(default=[])
    temporary_members = JSONField(default=[])
    invite = CharField(max_length=25)
    role = BigIntegerField()
    effect = ForeignKeyField(EffectModel, backref='pugs', null=True)

    class Meta:
        table_name = 'pugs'

    @classmethod
    async def create(cls, server_id: int, channel_id: int, invite: str, role: int) -> 'PugModel':
        return await objects.create(cls, server_id=server_id, channel_id=channel_id, invite=invite, role=role)

    @classmethod
    async def get(cls, channel_id: int) -> 'PugModel':
        return await objects.get(cls, channel_id=channel_id)

    @classmethod
    async def get_all(cls, server: ServerModel) -> list['PugModel']:
        q = cls.select().where(cls.server == server)
        return await objects.prefetch(q)


class InventoryModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    member = ForeignKeyField(MemberModel, backref='inventory')
    items = JSONField(default=[])

    class Meta:
        table_name = 'inventory'

    @classmethod
    async def create(cls, member: MemberModel, items=None) -> 'InventoryModel':
        if items is None:
            items = []
        return await objects.create(cls, member=member, items=items)

    @classmethod
    async def get(cls, member: MemberModel) -> Optional['InventoryModel']:
        try:
            return await objects.get(cls, member=member)
        except DoesNotExist:
            return None

    @classmethod
    async def get_all(cls) -> list['InventoryModel']:
        q = cls.select()
        return await objects.prefetch(q)


class StoreModel(BaseModel):
    server = ForeignKeyField(ServerModel, primary_key=True, backref='store')
    items = JSONField(default=[])
    next_refresh = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'stores'

    @classmethod
    async def create(cls, server: ServerModel, items: list = None, next_refresh: datetime = None) -> 'StoreModel':
        if items is None:
            items = []
        if next_refresh is None:
            next_refresh = get_aware_utc_now()
        return await objects.create(cls, server=server, items=items, next_refresh=next_refresh)

    @classmethod
    async def get(cls, server: ServerModel) -> Optional['StoreModel']:
        try:
            return await objects.get(cls, server=server)
        except DoesNotExist:
            return None

class TopicSubscriptionModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    member = ForeignKeyField(MemberModel, backref='topic_subscriptions', on_delete='CASCADE')
    topic = ForeignKeyField(TopicModel, backref='subscriptions', on_delete='CASCADE')
    created = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'topic_subscriptions'

    @classmethod
    async def create(cls, member: MemberModel, topic: TopicModel) -> 'TopicSubscriptionModel':
        existing = await cls.get(member, topic)
        if existing:
            return existing
        return await objects.create(cls, member=member, topic=topic)

    @classmethod
    async def get(cls, member: MemberModel, topic: TopicModel) -> Optional['TopicSubscriptionModel']:
        try:
            return await objects.get(cls, member=member, topic=topic)
        except DoesNotExist:
            return None

    @classmethod
    async def get_all(cls, member: MemberModel) -> list['TopicSubscriptionModel']:
        q = cls.select().where(cls.member == member)
        return await objects.prefetch(q, TopicModel.select())

    @classmethod
    async def get_all_by_topic(cls, topic: TopicModel) -> list['TopicSubscriptionModel']:
        q = cls.select().where(cls.topic == topic)
        return await objects.prefetch(q, MemberModel.select())


class StatisticModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    server_id = BigIntegerField()
    member_id = BigIntegerField(null=True)
    name = CharField(max_length=25, index=True)
    value = BigIntegerField(default=0)
    created = DatetimeTzField(default=get_aware_utc_now)
    updated = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'statistics'

    @classmethod
    async def create(cls, server_id: int, member_id: Optional[int], name: str, value: int) -> 'StatisticModel':
        model = await objects.create(cls, server_id=server_id, member_id=member_id, name=name, value=value)
        asyncio.create_task(StatisticHistoryModel.record(model))
        return model

    @classmethod
    async def get(cls, server_id: int, member_id: Optional[int], name: str) -> Optional['StatisticModel']:
        try:
            return await objects.get(cls, server_id=server_id, member_id=member_id, name=name)
        except DoesNotExist:
            return None

    @classmethod
    async def get_value(cls, server_id: int, member_id: Optional[int], name: str) -> int:
        try:
            statistic = await cls.get(server_id, member_id, name)
            if statistic:
                return statistic.value
            return 0
        except DoesNotExist:
            return 0

    @classmethod
    async def get_all(cls, server_id: int, member_id: Optional[int], *, stats: list[str] = None) -> list['StatisticModel']:
        if stats:
            q = cls.select().where(cls.server_id == server_id, cls.member_id == member_id, cls.name << stats)
        else:
            q = cls.select().where(cls.server_id == server_id, cls.member_id == member_id)
        return await objects.prefetch(q)

    @classmethod
    async def record_all(cls):
        q = cls.select()
        stats = await objects.prefetch(q)
        for stat in stats:
            await StatisticHistoryModel.record(stat)

    @classmethod
    async def increment(cls, server_id: int, member_id: Optional[int], name: str, amount: int = 1) -> None:
        q = (cls.update(value=cls.value + amount, updated=get_aware_utc_now())
             .where(cls.server_id == server_id, cls.member_id == member_id, cls.name == name))
        changed = await objects.execute(q)
        if changed == 0:
            await cls.create(server_id, member_id, name, amount)

    @classmethod
    async def set_value(cls, server_id: int, member_id: Optional[int], name: str, value: int) -> None:
        q = (cls.update(value=value, updated=get_aware_utc_now())
             .where(cls.server_id == server_id, cls.member_id == member_id, cls.name == name))
        changed = await objects.execute(q)
        if changed == 0:
            await cls.create(server_id, member_id, name, value)


class StatisticHistoryModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    statistic = ForeignKeyField(StatisticModel, backref='history', on_delete='CASCADE')
    value = BigIntegerField(default=0)
    created = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'statistic_history'

    @classmethod
    async def create(cls, stat: 'StatisticModel') -> 'StatisticHistoryModel':
        return await objects.create(cls, statistic=stat, value=stat.value)

    @classmethod
    async def get_latest(cls, stat: 'StatisticModel') -> Optional['StatisticHistoryModel']:
        q = cls.select().where(cls.statistic == stat).order_by(cls.created.desc())
        try:
            return await objects.get(q)
        except DoesNotExist:
            return None

    @classmethod
    async def get_earliest_since(cls, stat: 'StatisticModel', since: datetime.datetime) -> Optional['StatisticHistoryModel']:
        q = cls.select().where(cls.statistic == stat, cls.created > since).order_by(cls.created.asc())
        try:
            return await objects.get(q)
        except DoesNotExist:
            return 0

    @classmethod
    async def record(cls, stat: 'StatisticModel') -> None:
        latest = await cls.get_latest(stat)
        if latest:
            if latest.value != stat.value:
                await cls.create(stat)
        else:
            await cls.create(stat)

