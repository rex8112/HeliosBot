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


class RaceSettings(TypedDict):
    channel: Optional['TextChannel']
    message: Optional['Message']
    purse: int
    stake: int
    max_horses: 'MaxRaceHorses'
    type: 'RaceTypes'
    race_time: datetime.datetime
    betting_time: int
    phase: int
    can_run: bool


class StadiumSettings(TypedDict):
    season: int
    category: Optional[discord.CategoryChannel]
    announcement_id: int


class HorseListingSettings(TypedDict):
    min_bid: int
    max_bid: Optional[int]
    snipe_protection: int
    end_time: str


class AuctionSettings(TypedDict):
    start_time: str
    buy: bool


class GroupAuctionSettings(AuctionSettings):
    duration: int


class RotatingAuctionSettings(AuctionSettings):
    duration: int
    announcement: int
