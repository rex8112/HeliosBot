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
from typing import TypedDict, TYPE_CHECKING, Optional, Union, Dict, Tuple, List

import discord

if TYPE_CHECKING:
    from ..member import HeliosMember
    from discord import TextChannel, Message


Primitives = Union[int, float, bool, str]
ItemSerializable = Tuple[str, Union[Primitives, List]]
SettingsSerializable = Dict[str, Union[ItemSerializable, Primitives]]
PossibleSettings = Union['HorseSettings', 'EventRaceSettings']


class HorseSettings(TypedDict):
    breed: str
    gender: str
    age: int
    likes: int
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
    restrict_time: int
    phase: int
    can_run: bool
    invite_only: bool


class StadiumSettings(TypedDict):
    season: int
    season_active: bool
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
    any_canceled: bool


class GroupAuctionSettings(AuctionSettings):
    duration: int


class RotatingAuctionSettings(AuctionSettings):
    duration: int
    announcement: int
