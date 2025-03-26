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
import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from discord.ext.tasks import loop

if TYPE_CHECKING:
    from .server import Server


class TimeSlot:
    def __init__(self, start: datetime, end: datetime, schedule: 'Schedule', type: str, data: dict):
        self.type = type
        self.data = data
        self.schedule = schedule
        self.start = start
        self.end = end

        self.ran = False


    def key(self):
        return str(self.start) + str(self.end)

    def __hash__(self):
        return hash(self.key())


class Schedule:
    def __init__(self):
        self.now = datetime.now().astimezone()
        self.schedule: list['TimeSlot'] = []

        self._schedule_handlers = {}

        self._last_check = self.now

    def start(self):
        self.check.start()

    def stop(self):
        self.check.cancel()

    def handle(self, type: str):
        def decorator(func):
            self.add_handler(type, func)
            return func
        return decorator

    def add_handler(self, type: str, func):
        if type in self._schedule_handlers:
            self._schedule_handlers[type].append(func)
        else:
            self._schedule_handlers[type] = [func]

    def remove_handler(self, type: str, func):
        if type in self._schedule_handlers:
            self._schedule_handlers[type].remove(func)

    def extend_time(self, slot: TimeSlot, seconds: int):
        new_end = slot.end + timedelta(seconds=seconds)
        if self.is_conflicting_time(new_end):
            return False
        slot.end = new_end
        return True

    def set_end_time(self, slot: TimeSlot, end: datetime):
        if self.is_conflicting_time(end):
            return False
        slot.end = end
        return True

    def current_slot(self):
        for slot in self.schedule:
            if slot.start <= self.now <= slot.end:
                return slot
        return None

    def is_conflicting_time(self, dt: datetime):
        return self.get_conflicting_slot(dt) is not None

    def get_conflicting_slot(self, dt: datetime):
        for slot in self.schedule:
            if slot.start <= dt <= slot.end:
                return slot
        return None

    def create_slot(self, start: datetime, end: datetime, type: str, data: dict):
        slot = TimeSlot(start, end, self, type, data)
        if self.is_conflicting_time(slot.start) or self.is_conflicting_time(slot.end):
            return None
        self.schedule.append(slot)
        return slot

    def create_now_slot(self, seconds: int, type: str, data: dict, allow_dynamic_end=False, minimum_seconds=0):
        start = self.now
        if self.is_conflicting_time(start):
            return None

        # Decrease time until it is no longer conflicting.
        if allow_dynamic_end:
            conflicting_slot = self.get_conflicting_slot(start + timedelta(seconds=seconds))
            while conflicting_slot and seconds >= minimum_seconds:
                seconds = int((conflicting_slot.start - start).total_seconds()) - 1
                conflicting_slot = self.get_conflicting_slot(start + timedelta(seconds=seconds))

        if seconds < minimum_seconds:
            return None

        end = start + timedelta(seconds=seconds)
        if self.is_conflicting_time(end):
            return None
        return self.create_slot(start, end, type, data)

    @loop(seconds=1)
    async def check(self):
        self.now = datetime.now().astimezone()
        to_remove = []
        for slot in self.schedule:
            if slot.end <= self.now:
                to_remove.append(slot)
                if slot.ran:
                    for handler in self._schedule_handlers.get(slot.type + '_end', []):
                        try:
                            asyncio.create_task(handler(slot))
                        except (ValueError, AttributeError):
                            pass
            elif slot.start <= self.now and slot.ran is False:
                slot.ran = True
                for handler in self._schedule_handlers.get(slot.type, []):
                    try:
                        asyncio.create_task(handler(slot))
                    except (ValueError, AttributeError):
                        pass


        for slot in to_remove:
            self.schedule.remove(slot)