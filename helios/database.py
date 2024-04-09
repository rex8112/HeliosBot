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

import datetime
import json
from typing import TYPE_CHECKING

import peewee_async
from playhouse.migrate import *

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
                          EventModel, ViolationModel, DynamicVoiceModel, DynamicVoiceGroupModel, TopicModel])


def get_aware_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def migrate_members():
    migrator = MySQLMigrator(db)
    migrate(
        migrator.rename_table('members', 'oldmembers')
    )
    query = OldMemberModel.select()
    db.create_tables([MemberModel])
    with db.atomic():
        for old in query:
            server_id = old.server.id
            member_id = old.member_id
            templates = old.templates
            settings = old.settings
            flags = old.flags
            settings = json.loads(settings)
            activity_points = settings['activity_points']
            MemberModel.create(
                id=old.id,
                server_id=server_id,
                member_id=member_id,
                templates=templates,
                activity_points=activity_points,
                flags=flags
            )


# noinspection PyProtectedMember
def fix_transaction():
    migrator = MySQLMigrator(db)
    migrate(
        migrator.add_column(TransactionModel._meta.table_name, 'created_on', TransactionModel.created_on)
    )


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
        return self.async_save()

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


class OldMemberModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='oldmembers')
    member_id = BigIntegerField()
    templates = TextField(default='[]')
    settings = TextField(default='')
    flags = TextField(default='[]')

    class Meta:
        table_name = 'oldmembers'


class TransactionModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    member = ForeignKeyField(MemberModel, backref='transactions')
    payee = CharField(max_length=25)
    description = CharField(max_length=50)
    amount = IntegerField()
    created_on = DatetimeTzField(default=get_aware_utc_now)

    class Meta:
        table_name = 'transactions'


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
    target = CharField(80)
    duration = IntegerField()
    applied = BooleanField()
    applied_at = DatetimeTzField()
    extra = JSONField(default=dict())

    class Meta:
        table_name = 'topics'

    @classmethod
    async def new(cls, type: str, target: str, duration: int,
                  applied: bool, applied_at: datetime, extra: dict = None):
        if extra is None:
            extra = dict()
        return await objects.create(cls, type=type, target=target, duration=duration, applied=applied,
                                    applied_at=applied_at, extra=extra)

    @classmethod
    async def get_all(cls):
        q = cls.select()
        return await objects.prefetch(q)


class PugModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    channel_id = BigIntegerField()

