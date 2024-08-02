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

from datetime import datetime, timedelta
from typing import Hashable

from discord.utils import utcnow

cooldown = dict[Hashable, datetime]


class Cooldowns:
    def __init__(self):
        self.cooldowns: dict[str, cooldown] = {}

    def get_all(self, key: str):
        return self.cooldowns.get(key)

    def get(self, key: str, value: Hashable):
        return self.cooldowns.get(key, {}).get(value)

    def set(self, key: str, value: Hashable, time: datetime):
        if key not in self.cooldowns:
            self.cooldowns[key] = {}
        self.cooldowns[key][value] = time

    def set_duration(self, key: str, value: Hashable, duration: int):
        self.set(key, value, utcnow() + timedelta(seconds=duration))

    def on_cooldown(self, key: str, value: Hashable) -> bool:
        return self.get(key, value) and self.get(key, value) > utcnow()

    def remaining_time(self, key: str, value: Hashable):
        if self.on_cooldown(key, value):
            return self.get(key, value) - utcnow()
        return timedelta(seconds=0)

    def clear(self, key: str, value: Hashable):
        if key in self.cooldowns:
            self.cooldowns[key].pop(value, None)
            if not self.cooldowns[key]:
                self.cooldowns.pop(key)

