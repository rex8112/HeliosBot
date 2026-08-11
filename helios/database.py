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


class Statistic(Model):
    id = fields.IntField(pk=True)
    server = fields.ForeignKeyField(Server, related_name='statistics')
    user = fields.ForeignKeyField(User, related_name='statistics')
    name = fields.CharField(max_length=255)
    value = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Transaction(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(User, related_name='transactions')
    payee = fields.CharField(max_length=25)
    description = fields.CharField(max_length=50)
    amount = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Topic(Model):
    id = fields.IntField(pk=True)
    channel_id = fields.BigIntField()
    server = fields.ForeignKeyField(Server, related_name='topics')
    points = fields.IntField(default=0)
    state = fields.IntField(default=0)
    creator = fields.ForeignKeyField(User, related_name='created_topics', on_delete=fields.SET_NULL, null=True)
    archive_message = fields.BigIntField(null=True)
    archive_date = fields.DatetimeField(null=True)
    subscription = fields.ManyToManyField(User, related_name='topics', on_delete=fields.CASCADE, null=True) # MIGHT NEED TO BE CHANGED
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)