import datetime
from typing import TYPE_CHECKING, List

import discord

if TYPE_CHECKING:
    from ..types.horses import RaceTypes


class Event:
    def __init__(self, channel: discord.TextChannel, *,
                 type: str = 'daily',
                 start_time: datetime.datetime,
                 betting_time: int = 60 * 60 * 1,
                 registration_time: int = 60 * 60 * 6,
                 announcement_time: int = 60 * 60 * 12,
                 race_types: List[RaceTypes], ):
        self.channel = channel
        self.type = type
        self.start_time = start_time
        self.betting_time = betting_time
        self.registration_time = registration_time
        self.announcement_time = announcement_time
        self.race_types = race_types
