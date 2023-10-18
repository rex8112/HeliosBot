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

from typing import TYPE_CHECKING, Literal, Awaitable

from .database import EventModel

if TYPE_CHECKING:
    from .member import HeliosMember
    from .helios_bot import HeliosBot
    from peewee_async import Manager


EventTrigger = Literal['on_voice']


class EventManager:
    def __init__(self, bot: 'HeliosBot', db_manager: 'Manager'):
        self.db_manager = db_manager
        self.bot = bot

    async def add_action(self, trigger: EventTrigger, member: 'HeliosMember', action: str) -> Awaitable[EventModel]:
        return await self.db_manager.create(EventModel, trigger=trigger, action=action, target_id=member.id,
                                            server_id=member.server.id)

    async def get_actions(self, trigger: EventTrigger, member: 'HeliosMember') -> list[EventModel]:
        q = EventModel.select().where(EventModel.trigger == trigger, EventModel.target_id == member.id,
                                      EventModel.server_id == member.server.id)
        actions = await self.db_manager.prefetch(q)
        l: list[EventModel] = [x for x in actions]
        return l

    async def delete_action(self, action: EventModel):
        await self.db_manager.delete(action)

    async def clear_actions(self, trigger: EventTrigger, member: 'HeliosMember'):
        q = EventModel.select().where(EventModel.trigger == trigger, EventModel.target_id == member.id,
                                      EventModel.server_id == member.server.id)
        actions = await self.db_manager.prefetch(q)
        async with self.db_manager.atomic():
            for action in actions:
                await self.db_manager.delete(action)
