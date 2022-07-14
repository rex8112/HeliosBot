from typing import Union, TYPE_CHECKING, Any

from discord.abc import Snowflake

from ..exceptions import DecodingError

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
    def serialize(o: Any):
        name = type(o).__name__
        if isinstance(o, Snowflake):
            data = o.id
        else:
            raise DecodingError(f'Can not serialize object of type {type(o).__name__}')
        return name, data

    @staticmethod
    def deserialize(o: tuple[str, Union[str, int]], *, bot: 'HeliosBot' = None, guild: 'Guild' = None):
        name, data = o
        if name == 'Member':
            if not guild:
                raise ValueError(f'Argument guild required for type {name}.')
            return guild.get_member(data)
        elif name == 'Channel':
            if not guild:
                raise ValueError(f'Argument guild required for type {name}.')
            return guild.get_channel(data)
        else:
            raise NotImplemented
