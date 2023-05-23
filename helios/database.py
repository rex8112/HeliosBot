from peewee import *

db = SqliteDatabase('helios.db')


class Server(Model):
    id = BigIntegerField(primary_key=True, unique=True)
    name = CharField(max_length=26)
    settings = TextField(default="")
    flags = TextField(default="[]")

    class Meta:
        database = db


class Channel(Model):
    id = BigIntegerField(primary_key=True, unique=True)
    server = ForeignKeyField(Server, backref='server')
    type = CharField(max_length=26)
    settings = TextField(default='')
    flags = TextField(default='[]')

    class Meta:
        database = db


class Member(Model):
    id = AutoField(primary_key=True, unique=True)
    server = ForeignKeyField(Server, backref='server')
    member_id = BigIntegerField()
    templates = TextField(default='[]')
    settings = TextField(default='')
    flags = TextField(default='[]')

    class Meta:
        database = db
