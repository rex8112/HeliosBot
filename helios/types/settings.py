import datetime
from typing import TypedDict, TYPE_CHECKING, Optional, Union, Dict, Tuple, List

import discord

if TYPE_CHECKING:
    from ..member import HeliosMember
    from .horses import MaxRaceHorses, RaceTypes
    from discord import TextChannel, Message


Primitives = Union[int, float, bool, str]
ItemSerializable = Tuple[str, Union[Primitives, List]]
SettingsSerializable = Dict[str, Union[ItemSerializable, Primitives]]
PossibleSettings = Union['HorseSettings', 'EventRaceSettings']


class HorseSettings(TypedDict):
    breed: str
    gender: str
    age: int
    owner: Optional['HeliosMember']
    wins: int


class EventRaceSettings(TypedDict):
    channel: Optional['TextChannel']
    message: Optional['Message']
    purse: int
    stake: int
    max_horses: 'MaxRaceHorses'
    type: 'RaceTypes'
    race_time: datetime.datetime
    betting_time: int
    phase: int


class StadiumSettings(TypedDict):
    season: int
    category: Optional[discord.CategoryChannel]