# Tortoise Database
from tortoise.models import Model
from tortoise import fields


class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=255)
    activity_points = fields.IntField(default=0)
    points = fields.IntField(default=0)
    flags = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Server(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=255)
    settings = fields.JSONField(default=dict)
    flags = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Statistics(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField(Server, related_name='statistics')
    user = fields.ForeignKeyField(User, related_name='statistics')
    name = fields.CharField(max_length=255)
    value = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)