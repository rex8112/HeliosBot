#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
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
from datetime import datetime

import discord


class Game:
    def __init__(self, name: str, *, display_name: str = None, icon: str = None, alias: list[str] = None,
                 play_time: int = 0, last_day_playtime: int = 0, last_played: datetime = None):
        self.name = name
        self.display_name = display_name or name
        self.alias = alias or []
        self.icon = icon
        self.play_time = play_time
        self.last_day_playtime = last_day_playtime
        self.last_played = last_played or discord.utils.utcnow()

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['name'], display_name=data.get('display_name'), icon=data.get('icon'),
                   alias=data.get('alias', []), play_time=data.get('play_time', 0),
                   last_day_playtime=data.get('last_day_playtime', 0), last_played=data.get('last_played'))

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'display_name': self.display_name,
            'icon': self.icon,
            'alias': self.alias,
            'play_time': self.play_time,
            'last_day_playtime': self.last_day_playtime,
            'last_played': self.last_played
        }

    @classmethod
    def from_activity(cls, activity: discord.Activity) -> 'Game':
        return cls(activity.name, icon=activity.large_image_url)

    def __str__(self):
        return self.display_name

    def __repr__(self):
        return f'<Game name={self.name} display_name={self.display_name}>'
