import datetime
import json

import peewee_async
from playhouse.migrate import *

db = peewee_async.MySQLDatabase('heliosTesting', user='helios', password='bot', host='192.168.40.101', port=3306)
objects = peewee_async.Manager(db)


def update_model_instance(model: Model, data: dict):
    for key, value in data.items():
        old = getattr(model, key)
        if old != value:
            setattr(model, key, value)


def initialize_db():
    db.connect()
    db.create_tables([ServerModel, MemberModel, ChannelModel, TransactionModel,
                      EventModel])


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


class DatetimeTzField(Field):
    field_type = 'DATETIME'

    def db_value(self, value: datetime.datetime) -> str:
        if value:
            return value.strftime('%Y-%m-%d %H:%M:%S')

    def python_value(self, value: str) -> datetime.datetime:
        if value:
            return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)


class BaseModel(Model):
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


class PugModel(BaseModel):
    id = AutoField(primary_key=True, unique=True)
    channel_id = BigIntegerField()

