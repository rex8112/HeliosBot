import peewee_async
from peewee import *

db = peewee_async.MySQLDatabase('helios.db')
objects = peewee_async.Manager(db)


def update_model_instance(model: Model, data: dict):
    for key, value in data.items():
        old = getattr(model, key)
        if old != value:
            setattr(model, key, value)


class ServerModel(Model):
    id = BigIntegerField(primary_key=True, unique=True)
    name = CharField(max_length=26)
    settings = TextField(default="")
    flags = TextField(default="[]")

    class Meta:
        database = db


class ChannelModel(Model):
    id = BigIntegerField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='server')
    type = CharField(max_length=26)
    settings = TextField(default='')
    flags = TextField(default='[]')

    class Meta:
        database = db


class MemberModel(Model):
    id = AutoField(primary_key=True, unique=True)
    server = ForeignKeyField(ServerModel, backref='server')
    member_id = BigIntegerField()
    templates = TextField(default='[]')
    settings = TextField(default='')
    flags = TextField(default='[]')

    class Meta:
        database = db
