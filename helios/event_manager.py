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

from typing import TYPE_CHECKING, Literal, Awaitable, Union

import discord.abc

from .database import EventModel

if TYPE_CHECKING:
    from .member import HeliosMember
    from .helios_bot import HeliosBot


EventTrigger = Literal['on_voice', 'on_start']


class EventManager:
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    async def add_action(self, trigger: EventTrigger, member: Union['HeliosMember', discord.abc.Snowflake],
                         action: str) -> Awaitable[EventModel]:
        return await EventModel.create(trigger=trigger, action=action, target_id=member.id,
                                       server_id=member.server.id if getattr(member, 'server', None) else member.guild.id)

    async def get_actions(self, trigger: EventTrigger, member: 'HeliosMember') -> list[EventModel]:
        actions = await EventModel.filter(trigger=trigger, target_id=member.id, server=member.server.db_entry)
        l: list[EventModel] = [x for x in actions]
        return l

    async def get_specific_actions(self, trigger: EventTrigger, member: 'HeliosMember', action: str):
        actions = await EventModel.filter(trigger=trigger, target_id=member.id, server=member.server.db_entry, action=action)
        l: list[EventModel] = [x for x in actions]
        return l

    async def get_all_trigger_actions(self, trigger: EventTrigger):
        actions = await EventModel.filter(trigger=trigger)
        l: list[EventModel] = list(actions)
        return l

    async def delete_action(self, action: EventModel):
        await action.delete()

    async def clear_actions(self, trigger: EventTrigger, member: Union['HeliosMember', discord.abc.Snowflake] = None):
        if member is None:
            await EventModel.filter(trigger=trigger).delete()
        else:
            await EventModel.filter(trigger=trigger, target_id=member.id,
                                    server_id=member.server.db_entry).delete()
