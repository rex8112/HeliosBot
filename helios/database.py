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
from typing import TYPE_CHECKING, Optional, Iterable

import discord.utils
from tortoise import Tortoise
from tortoise import fields
from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q, F
from tortoise.functions import Sum
from tortoise.models import Model

from .tools.config import Config

if TYPE_CHECKING:
    pass

__all__ = (
    'initialize_db',
    'close_db',
    'VersionModel',
    'ServerModel',
    'ChannelModel',
    'MemberModel',
    'TransactionModel',
    'EventModel',
    'DynamicVoiceGroupModel',
    'DynamicVoiceModel',
    'TopicModel',
    'EffectModel',
    'ThemeModel',
    'BlackjackModel',
    'DailyModel',
    'GameModel',
    'GameAliasModel',
    'PugModel',
    'InventoryModel',
    'TopicSubscriptionModel',
    'StoreModel',
    'StatisticModel',
    'StatisticHistoryModel'
)

settings = Config.from_file_path()

# db = peewee_async.MySQLDatabase(settings.db_path, user=settings.db_username, password=settings.db_password,
#                                 host=settings.db_host, port=int(settings.db_port), charset='utf8mb4')
# db.set_allow_sync(False)
# objects = peewee_async.Manager(db)


async def initialize_db():
    # with db.allow_sync():
    #     db.connect()
    #     db.create_tables([ServerModel, MemberModel, ChannelModel, TransactionModel,
    #                       EventModel, ViolationModel, DynamicVoiceModel, DynamicVoiceGroupModel, TopicModel,
    #                       EffectModel, ThemeModel, BlackjackModel, DailyModel, GameModel, GameAliasModel, PugModel,
    #                       InventoryModel, StoreModel, TopicSubscriptionModel, StatisticModel, StatisticHistoryModel])
    await Tortoise.init(
        config={
            'connections': {
                'default': {
                    'engine': 'tortoise.backends.mysql',
                    'credentials': {
                        'host': settings.db_host,
                        'port': settings.db_port,
                        'user': settings.db_username,
                        'password': settings.db_password,
                        'database': settings.db_path,
                    }
                }
            },
            'apps': {
                'models': {
                    'models': ['helios.database'],
                    'default_connection': 'default',
                }
            }
        },
        modules={'app': ['helios.database']},

    )
    await Tortoise.generate_schemas(safe=True)

async def initialize_test_db():
    await Tortoise.init(
        db_url='sqlite://:memory:',
        modules={'app': ['helios.database']},
    )
    await Tortoise.generate_schemas()

async def close_db():
    await Tortoise.close_connections()


def get_aware_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


# class JSONField(Field):
#     field_type = 'text'
#
#     def db_value(self, value):
#         return json.dumps(value)
#
#     def python_value(self, value):
#         return json.loads(value)


# class DatetimeTzField(Field):
#     field_type = 'DATETIME'
#
#     def db_value(self, value: datetime.datetime) -> str:
#         if value:
#             return value.strftime('%Y-%m-%d %H:%M:%S')
#
#     def python_value(self, value: datetime.datetime) -> datetime.datetime:
#         if value:
#             return value.replace(tzinfo=datetime.timezone.utc)


class BaseModel(Model):
    @staticmethod
    def update_model_instance(model: Model, data: dict):
        """Update a model instance with a dictionary."""
        model.update_from_dict(data)

    def async_save(self, only: Optional[Iterable[str]] = None):
        """Save the model instance asynchronously."""
        return self.save(update_fields=only)

    def async_update(self, **kwargs):
        """Update the model instance asynchronously."""
        self.update_model_instance(self, kwargs)
        return self.async_save(only=kwargs.keys())

    def async_delete(self):
        """Delete the model instance asynchronously."""
        return self.delete()

    class Meta:
        abstract = True


class VersionModel(BaseModel):
    version = fields.CharField(max_length=12)

    class Meta:
        table = 'version'


class ServerModel(BaseModel):
    id = fields.BigIntField(primary_key=True)
    name = fields.CharField(max_length=26)
    settings = fields.JSONField(default={})
    flags = fields.JSONField(default=[])

    members: fields.ReverseRelation[MemberModel]
    channels: fields.ReverseRelation[ChannelModel]

    class Meta:
        table = 'servers'


class ChannelModel(BaseModel):
    id = fields.BigIntField(primary_key=True)
    server = fields.ForeignKeyField(ServerModel, related_name='channels')
    type = fields.CharField(max_length=26)
    settings = fields.JSONField(default={})
    flags = fields.JSONField(default=[])

    class Meta:
        table = 'channels'


class MemberModel(BaseModel):
    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField(ServerModel, related_name='members')
    member_id = fields.BigIntField()
    activity_points = fields.IntField(default=0)
    points = fields.IntField(default=0)
    ap_paid = fields.IntField(default=0)
    templates = fields.JSONField(default=[])
    flags = fields.JSONField(default=[])

    class Meta:
        table = 'members'

    @staticmethod
    async def create_model(server: ServerModel, **kwargs):
        """Create a new model instance in the database."""
        return await MemberModel.create(server=server, **kwargs)


class TransactionModel(BaseModel):
    id = fields.IntField(primary_key=True)
    member = fields.ForeignKeyField(MemberModel, related_name='transactions')
    payee = fields.CharField(max_length=25)
    description = fields.CharField(max_length=50)
    amount = fields.IntField()
    created_on = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'transactions'

    @staticmethod
    async def get_transactions_paginated(member: 'MemberModel', page: int, limit: int) -> list['TransactionModel']:
        # q = (TransactionModel.select().where(TransactionModel.member_id == member.db_id)
        #      .order_by(TransactionModel.id.desc()).paginate(page, limit))
        q = await TransactionModel.all().filter(member=member).offset(page * limit).limit(limit).order_by('-id').prefetch_related('member')
        return q

    @staticmethod
    async def get_24hr_change(member: 'MemberModel'):
        ago = discord.utils.utcnow() - datetime.timedelta(days=1)
        q = await TransactionModel.filter(member=member, created_on__gte=ago).annotate(day_change=Sum('amount')).first()
        return q.day_change

    @staticmethod
    async def get_24hr_transfers_out(member: 'MemberModel'):
        ago = discord.utils.utcnow() - datetime.timedelta(days=1)
        q = await (TransactionModel.filter(member=member, created_on__gte=ago,
                                          amount__lt=0, description='Transferred Points')
                   .annotate(day_change=Sum('amount')).first())
        return int(q.day_change) if q.day_change else 0

    @staticmethod
    async def calculate_balance(member: 'MemberModel'):
        q = await TransactionModel.filter(member=member).annotate(balance=Sum('amount')).first()
        return q.balance


class EventModel(BaseModel):
    id = fields.IntField(primary_key=True)
    trigger = fields.CharField(max_length=20)
    action = fields.CharField(max_length=25)
    server = fields.ForeignKeyField(ServerModel, related_name='startups', null=True)
    target_id = fields.BigIntField()

    class Meta:
        table = 'events'


# class AuditLogModel(BaseModel):
#     id = AutoField(primary_key=True, unique=True)
#     action = CharField(max_length=25)
#     user = ForeignKeyField(MemberModel, related_name='audits')
#     target = ForeignKeyField(MemberModel, related_name='audits_target')
#     description = CharField(max_length=50, null=True)
#     created = DatetimeTzField(default=datetime.datetime.now)
#
#     @staticmethod
#     async def get_target_temp_mutes(target_id: int) -> list['AuditLogModel']:
#         q = AuditLogModel.select().where(AuditLogModel.target_id == target_id, AuditLogModel.action == 'temp_mute')
#         audits = await objects.prefetch(q)
#         return list(audits)
#
#     class Meta:
#         table = 'auditlogs'


# class CourtModel(BaseModel):
#     id = AutoField(primary_key=True, unique=True)
#     type = IntegerField()
#     date = DatetimeTzField()
#     judge = ForeignKeyField(MemberModel, related_name='judges')
#     decision = BooleanField(null=True)
#     jury = JSONField(default=[])
#
#     class Meta:
#         table = 'courts'


# class CaseModel(BaseModel):
#     id = AutoField(primary_key=True, unique=True)
#     plaintiff = ForeignKeyField(MemberModel, related_name='plaintiff_cases')
#     defendant = ForeignKeyField(MemberModel, related_name='defendant_cases')
#     court = ForeignKeyField(CourtModel, related_name='cases')
#     punishment = JSONField(default={})
#     punished = BooleanField(default=False)
#     finished = DatetimeTzField(null=True)
#     created = DatetimeTzField(default=get_aware_utc_now)
#
#     class Meta:
#         table = 'cases'


class DynamicVoiceGroupModel(BaseModel):
    """A model for dynamic voice groups."""
    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField(ServerModel, related_name='voice_groups')
    min = fields.IntField()
    min_empty = fields.IntField(default=1)
    max = fields.IntField(default=0)
    template = fields.CharField(max_length=25)
    game_template = fields.CharField(max_length=25)

    class Meta:
        table = 'dynamicvoicegroups'

    @staticmethod
    async def get_all(server: ServerModel) -> list['DynamicVoiceGroupModel']:
        """Get all models for a server."""
        q = await DynamicVoiceGroupModel.filter(server=server).prefetch_related('server')
        return q

    @staticmethod
    async def create_model(server: ServerModel, **kwargs):
        """Create a new model instance in the database."""
        q = await DynamicVoiceGroupModel.create(server=server, **kwargs)
        return q


class DynamicVoiceModel(BaseModel):
    """A model for dynamic voice channels."""
    channel = fields.BigIntField(primary_key=True)
    server = fields.ForeignKeyField(ServerModel, related_name='dynamic_voices')
    settings = fields.JSONField(default={})

    class Meta:
        table = 'dynamicvoices'

    @staticmethod
    async def get_all(server: ServerModel) -> list['DynamicVoiceModel']:
        """Get all models for a server."""
        q = await DynamicVoiceModel.filter(server=server).prefetch_related('server')

        return q

    @staticmethod
    async def get_by_channel(channel: int) -> 'DynamicVoiceModel':
        """Get a model by channel ID."""
        q = await DynamicVoiceModel.filter(channel=channel).first()
        return q

    @staticmethod
    async def create_model(server: ServerModel, **kwargs):
        """Create a new model instance in the database."""
        q = await DynamicVoiceModel.create(server=server, **kwargs)
        return q


class TopicModel(BaseModel):
    id = fields.IntField(primary_key=True)
    channel_id = fields.BigIntField(unique=True)
    server = fields.ForeignKeyField(ServerModel, related_name='topics')
    points = fields.IntField()
    state = fields.IntField()
    creator = fields.ForeignKeyField(MemberModel, related_name='topics', null=True)
    archive_message = fields.BigIntField(null=True)
    archive_date = fields.DatetimeField(null=True)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'topics'

    def async_save(self, only=None):
        self.updated = get_aware_utc_now()
        return super().async_save(only=only)

    @staticmethod
    async def async_create(channel_id: int, server: ServerModel, creator: MemberModel, points: int, state: int):
        q = await TopicModel.create(channel_id=channel_id, server=server, creator=creator, points=points, state=state)
        return q

    @staticmethod
    async def get_by_channel(channel_id: int) -> 'TopicModel':
        q = await TopicModel.filter(channel_id=channel_id).prefetch_related('server', 'creator').first()
        return q

    @staticmethod
    async def get_all(server: ServerModel) -> list['TopicModel']:
        q = await TopicModel.filter(server=server).prefetch_related('server', 'creator')
        return q


class EffectModel(BaseModel):
    id = fields.IntField(primary_key=True)
    type = fields.CharField(30)
    target = fields.CharField(80)
    duration = fields.IntField()
    applied = fields.BooleanField()
    applied_at = fields.DatetimeField(null=True)
    extra = fields.JSONField(default=dict())

    class Meta:
        table = 'effects'

    @classmethod
    async def new(cls, type: str, target: str, duration: int,
                  applied: bool, applied_at: datetime.datetime, extra: dict = None):
        if extra is None:
            extra = dict()
        q = await cls.create(type=type, target=target, duration=duration, applied=applied,
                                     applied_at=applied_at, extra=extra)
        return q

    @classmethod
    async def get_all(cls) -> list['EffectModel']:
        q = await cls.all()
        return q


class ThemeModel(BaseModel):
    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField(ServerModel, related_name='themes')
    name = fields.CharField(max_length=25, unique=True)
    roles = fields.JSONField(default=[])
    groups = fields.JSONField(default=[])
    owner = fields.ForeignKeyField(MemberModel, related_name='themes', null=True)
    editable = fields.BooleanField(default=True)
    current = fields.BooleanField(default=False)
    sort_stat = fields.CharField(max_length=25, default='points')
    sort_type = fields.CharField(max_length=25, default='total')
    afk_channel = fields.CharField(max_length=25, default='💤 AFK Channel')
    banner_url = fields.CharField(max_length=255, null=True)
    created = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'themes'

    @classmethod
    async def get_all(cls, server: ServerModel) -> list['ThemeModel']:
        q = await cls.filter(server=server).prefetch_related('server', 'owner')
        return q

    @classmethod
    async def get_current(cls, server: ServerModel) -> Optional['ThemeModel']:
        q = await cls.filter(server=server, current=True).first()
        return q

    @classmethod
    async def get_themes(cls, server: ServerModel, owner: MemberModel = None):
        """Get all themes for a server, optionally filtered by owner."""
        if owner:
            q = await cls.filter(server=server, owner=owner).prefetch_related('server', 'owner')
        else:
            q = await cls.filter(server=server).prefetch_related('server', 'owner')
        return q

    @classmethod
    async def get_by_name(cls, name: str) -> Optional['ThemeModel']:
        """Get a theme by its name."""
        q = await cls.filter(name=name).prefetch_related('server', 'owner').first()
        return q

    @classmethod
    async def create_model(cls, server: ServerModel, owner: MemberModel, name: str, roles: list[dict], groups: list[dict]) -> 'ThemeModel':
        q = await cls.create(server=server, owner=owner, name=name, roles=roles, groups=groups)
        return q


class BlackjackModel(BaseModel):
    id = fields.IntField(primary_key=True)
    players = fields.JSONField(default=[])
    hands = fields.JSONField(default=[])
    bets = fields.JSONField(default=[])
    powerups = fields.JSONField(default=[])
    winnings = fields.JSONField(default=[])
    dealer_hand = fields.JSONField(default=[])
    created = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'blackjack'

    @classmethod
    async def create_model(cls, players: list) -> 'BlackjackModel':
        q = await cls.create(players=players)
        return q


class DailyModel(BaseModel):
    id = fields.IntField(primary_key=True)
    member = fields.ForeignKeyField(MemberModel, related_name='dailies')
    claimed = fields.IntField(default=-1)

    class Meta:
        table = 'dailies'

    @classmethod
    async def claim(cls, member: MemberModel, day: int):
        try:
            daily = await cls.get(member=member)
            if daily.claimed != day:
                daily.claimed = day
                await daily.save(update_fields=['claimed'])
                return True
            return False
        except DoesNotExist:
            await cls.create(member=member, claimed=day)
            return True

    @classmethod
    async def is_claimed(cls, member: MemberModel, day: int):
        try:
            daily = await cls.get(member=member)
            return daily.claimed == day
        except DoesNotExist:
            return False


class GameModel(BaseModel):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=52, unique=True)
    display_name = fields.CharField(max_length=52)
    icon = fields.CharField(max_length=255)
    play_time = fields.IntField(default=0)
    last_day_playtime = fields.IntField(default=0)
    last_played = fields.DatetimeField(auto_now_add=True)

    aliases: fields.ReverseRelation['GameAliasModel']

    class Meta:
        table = 'games'

    @classmethod
    async def create_game(cls, name: str, display_name: str, icon: str) -> 'GameModel':
        q = await cls.create(name=name, display_name=display_name, icon=icon)
        return q

    async def delete_game(self):
        await self.delete()

    @classmethod
    async def find_game(cls, name: str) -> Optional['GameModel']:
        """Find a game by name or alias."""
        # q = cls.select().join(GameAliasModel, join_type=JOIN.LEFT_OUTER).where((cls.name == name) | (GameAliasModel.alias == name))
        q = await cls.filter(Q(name=name) | Q(aliases__alias=name)).prefetch_related('aliases').first()
        try:
            res = q
            if res:
                return res
            return None
        except DoesNotExist:
            return None

    @classmethod
    async def set_day_playtime(cls):
        """Set the last day playtime to the current playtime."""
        # q = cls.select().where(cls.play_time > cls.last_day_playtime)
        q = await cls.filter(play_time__gt=F('last_day_playtime')).prefetch_related('aliases').update(last_day_playtime=F('play_time'))

    async def add_playtime(self, time: int):
        """Add playtime to the game."""
        self.play_time += time
        self.last_played = get_aware_utc_now()
        return await self.async_save(only=('play_time', 'last_played'))

    async def add_alias(self, alias: str):
        """Add an alias to the game."""
        q = await self.aliases.create(alias=alias)
        return q

    async def remove_alias(self, alias: str):
        """Remove an alias from the game."""
        q = await self.aliases.filter(alias=alias).delete()
        return q


class GameAliasModel(BaseModel):
    id = fields.IntField(primary_key=True)
    game = fields.ForeignKeyField(GameModel, related_name='aliases', on_delete=fields.CASCADE)
    alias = fields.CharField(max_length=52, unique=True)

    class Meta:
        table = 'game_aliases'


# class Lottery(BaseModel):
#     id = AutoField(primary_key=True, unique=True)
#     game_type = CharField(max_length=16)
#     pool = IntegerField()
#     frequency = IntegerField()
#     numbers = IntegerField()
#     range = IntegerField()
#     next_game = DatetimeTzField()
#     tickets = JSONField(default=[])
#
#     class Meta:
#         table = 'lotteries'


class PugModel(BaseModel):
    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField(ServerModel, related_name='pugs')
    channel = fields.ForeignKeyField(DynamicVoiceModel, related_name='pugs', unique=True)
    server_members = fields.JSONField(default=[])
    temporary_members = fields.JSONField(default=[])
    invite = fields.CharField(max_length=25)
    role = fields.BigIntField()
    effect = fields.ForeignKeyField(EffectModel, related_name='pugs', null=True)

    class Meta:
        table = 'pugs'

    @classmethod
    async def create_pug(cls, server_id: int, channel_id: int, invite: str, role: int) -> 'PugModel':
        q = await cls.create(server_id=server_id, channel_id=channel_id, invite=invite, role=role)
        return q

    @classmethod
    async def get_by_channel(cls, channel_id: int) -> 'PugModel':
        q = await cls.filter(channel_id=channel_id).first()
        return q

    @classmethod
    async def get_all(cls, server: ServerModel) -> list['PugModel']:
        q = await cls.filter(server=server)
        return q


class InventoryModel(BaseModel):
    id = fields.IntField(primary_key=True,)
    member = fields.ForeignKeyField(MemberModel, related_name='inventory')
    items = fields.JSONField(default=[])

    class Meta:
        table = 'inventory'

    @classmethod
    async def create_inventory(cls, member: MemberModel, items=None) -> 'InventoryModel':
        if items is None:
            items = []
        q = await cls.create(member=member, items=items)
        return q

    @classmethod
    async def get_by_member(cls, member: MemberModel) -> Optional['InventoryModel']:
        try:
            q = await cls.filter(member=member).prefetch_related('member').first()
            return q
        except DoesNotExist:
            return None

    @classmethod
    async def get_all(cls) -> list['InventoryModel']:
        q = await cls.all()
        return q


class StoreModel(BaseModel):
    server = fields.ForeignKeyField(ServerModel, primary_key=True, backref='store')
    items = fields.JSONField(default=[])
    next_refresh = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'stores'

    @classmethod
    async def create_store(cls, server: ServerModel, items: list = None, next_refresh: datetime.datetime = None) -> 'StoreModel':
        if items is None:
            items = []
        if next_refresh is None:
            next_refresh = get_aware_utc_now()
        q = await cls.create(server=server, items=items, next_refresh=next_refresh)
        return q

    @classmethod
    async def get_by_server(cls, server: ServerModel) -> Optional['StoreModel']:
        try:
            q = await cls.filter(server=server).first()
            return q
        except DoesNotExist:
            return None

class TopicSubscriptionModel(BaseModel):
    id = fields.IntField(primary_key=True)
    member = fields.ForeignKeyField(MemberModel, related_name='topic_subscriptions', on_delete='CASCADE')
    topic = fields.ForeignKeyField(TopicModel, related_name='subscriptions', on_delete='CASCADE')
    created = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'topic_subscriptions'

    @classmethod
    async def create_topic_sub(cls, member: MemberModel, topic: TopicModel) -> 'TopicSubscriptionModel':
        existing = await cls.get_or_none(member=member, topic=topic)
        if existing:
            return existing
        return await cls.create(member=member, topic=topic)

    @classmethod
    async def get_by_member_topic(cls, member: MemberModel, topic: TopicModel) -> Optional['TopicSubscriptionModel']:
        try:
            return await cls.get(member=member, topic=topic)
        except DoesNotExist:
            return None

    @classmethod
    async def get_all_by_member(cls, member: MemberModel) -> list['TopicSubscriptionModel']:
        q = await cls.filter(member=member)
        return q

    @classmethod
    async def get_all_by_topic(cls, topic: TopicModel) -> list['TopicSubscriptionModel']:
        q = await cls.filter(topic=topic)
        return q


class StatisticModel(BaseModel):
    id = fields.IntField(primary_key=True)
    server_id = fields.BigIntField()
    member_id = fields.BigIntField(null=True)
    name = fields.CharField(max_length=25, index=True)
    value = fields.BigIntField(default=0)
    created = fields.DatetimeField(auto_now_add=True)
    updated = fields.DatetimeField(auto_now=True)

    history: fields.ReverseRelation['StatisticHistoryModel']

    class Meta:
        table = 'statistics'

    @classmethod
    async def create_stat(cls, server_id: int, member_id: Optional[int], name: str, value: int) -> 'StatisticModel':
        model = await cls.create(server_id=server_id, member_id=member_id, name=name, value=value)
        asyncio.create_task(StatisticHistoryModel.record(model))
        return model

    @classmethod
    async def get_by_member_stat_name(cls, server_id: int, member_id: Optional[int], name: str) -> Optional['StatisticModel']:
        try:
            return await cls.filter(server_id=server_id, member_id=member_id, name=name).first()
        except DoesNotExist:
            return None

    @classmethod
    async def get_value(cls, server_id: int, member_id: Optional[int], name: str) -> int:
        try:
            statistic = await cls.get_by_member_stat_name(server_id, member_id, name)
            if statistic:
                return statistic.value
            return 0
        except DoesNotExist:
            return 0

    @classmethod
    async def get_all(cls, server_id: int, member_id: Optional[int], *, stats: list[str] = None) -> list['StatisticModel']:
        if stats:
            q = await cls.filter(server_id=server_id, member_id=member_id, name__in=stats)
        else:
            q = await cls.filter(server_id=server_id, member_id=member_id)
        return q

    @classmethod
    async def record_all(cls):
        q = await cls.all()
        stats = q
        for stat in stats:
            await StatisticHistoryModel.record(stat)

    @classmethod
    async def increment(cls, server_id: int, member_id: Optional[int], name: str, amount: int = 1) -> None:
        # q = (cls.update(value=cls.value + amount, updated=get_aware_utc_now())
        #      .where(cls.server_id == server_id, cls.member_id == member_id, cls.name == name))
        q = await cls.filter(server_id=server_id, member_id=member_id, name=name).update(value=F('value') + amount)
        changed = q
        if changed == 0:
            await cls.create_stat(server_id, member_id, name, amount)

    @classmethod
    async def set_value(cls, server_id: int, member_id: Optional[int], name: str, value: int) -> None:
        # q = (cls.update(value=value, updated=get_aware_utc_now())
        #      .where(cls.server_id == server_id, cls.member_id == member_id, cls.name == name))
        q = await cls.filter(server_id=server_id, member_id=member_id, name=name).update(value=value)
        changed = q
        if changed == 0:
            await cls.create_stat(server_id, member_id, name, value)


class StatisticHistoryModel(BaseModel):
    id = fields.IntField(primary_key=True)
    statistic = fields.ForeignKeyField(StatisticModel, related_name='history', on_delete=fields.CASCADE)
    value = fields.BigIntField(default=0)
    created = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'statistic_history'

    @classmethod
    async def create_history(cls, stat: 'StatisticModel') -> 'StatisticHistoryModel':
        return await cls.create(statistic=stat, value=stat.value)

    @classmethod
    async def get_latest(cls, stat: 'StatisticModel') -> Optional['StatisticHistoryModel']:
        q = await cls.filter(statistic=stat).order_by('-created').first()
        return q

    @classmethod
    async def get_earliest_since(cls, stat: 'StatisticModel', since: datetime.datetime) -> Optional['StatisticHistoryModel']:
        q = await cls.filter(statistic=stat, created__gt=since).order_by('created').first()
        return q

    @classmethod
    async def record(cls, stat: 'StatisticModel') -> None:
        latest = await cls.get_latest(stat)
        if latest:
            if latest.value != stat.value:
                await cls.create_history(stat)
        else:
            await cls.create_history(stat)

