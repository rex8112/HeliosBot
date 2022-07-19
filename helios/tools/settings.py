from typing import Union, TYPE_CHECKING, Any

from discord.abc import Snowflake

from ..exceptions import DecodingError
from ..types.settings import ItemSerializable

if TYPE_CHECKING:
    from ..helios_bot import HeliosBot
    from discord import Guild


class Settings:
    def __init__(self, data: dict, *, bot: 'HeliosBot' = None, guild: 'Guild' = None):
        for k, v in data.items():
            try:
                if self.__getattribute__(k):
                    raise AttributeError(f'Attribute {k} already exists')
            except AttributeError:
                ...
            if isinstance(v, tuple):
                try:
                    self.__setattr__(k, Item.deserialize(v, bot=bot, guild=guild))
                except DecodingError:
                    self.__setattr__(k, v)
            else:
                self.__setattr__(k, v)

    def to_dict(self) -> dict:
        d = dict()
        for k, v in self.__dict__.items():
            try:
                new_value = Item.serialize(v)
            except DecodingError:
                new_value = v
            d[k] = new_value
        return d


class Item:
    @staticmethod
    def serialize(o: Any) -> Union[ItemSerializable, Any]:
        name = type(o).__name__
        if isinstance(o, Snowflake):
            data = o.id
        elif isinstance(o, (int, float, str, bool)):
            data = o
        else:
            try:
                data = o.serialize()
            except AttributeError:
                raise DecodingError(f'Can not serialize object of type {type(o).__name__}')
        return name, data

    @staticmethod
    def deserialize(o: ItemSerializable, *, bot: 'HeliosBot' = None, guild: 'Guild' = None):
        name, data = o
        if name == 'Member':
            if not guild:
                raise ValueError(f'Argument guild required for type {name}.')
            return guild.get_member(data)
        elif name == 'Channel':
            if not guild:
                raise ValueError(f'Argument guild required for type {name}.')
            return guild.get_channel(data)
        elif name == 'HeliosMember':
            if not guild or not bot:
                raise(ValueError(f'Argument guild and bot required for type {name}'))
            server = bot.servers.get(guild.id)
            return server.members.get(data)
        else:
            raise NotImplemented

    @staticmethod
    def serialize_list(el: list[Any]) -> list[ItemSerializable]:
        new_list = []
        for o in el:
            new_list.append(Item.serialize(o))
        return new_list

    @staticmethod
    def deserialize_list(el: list[ItemSerializable], *, bot: 'HeliosBot' = None, guild: 'Guild' = None) -> list[Any]:
        new_list = []
        for o in el:
            new_list.append(Item.deserialize(o, bot=bot, guild=guild))
        return new_list

    @staticmethod
    def serialize_dict(d: dict[str, Any]) -> dict[str, ItemSerializable]:
        new_d = {}
        for k, v in d.items():
            new_d[k] = Item.serialize(v)
        return new_d

    @staticmethod
    def deserialize_dict(d: dict[str, ItemSerializable], *, bot: 'HeliosBot' = None, guild: 'Guild' = None):
        new_d = {}
        for k, v in d.items():
            new_d[k] = Item.deserialize(v, bot=bot, guild=guild)
        return new_d
