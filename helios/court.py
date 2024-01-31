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

from typing import TYPE_CHECKING

from discord.ext import tasks

from .database import ViolationModel, objects, MemberModel
from .enums import ViolationStates
from .violation import Violation

if TYPE_CHECKING:
    from .server import Server
    from .member import HeliosMember


class Court:
    def __init__(self, server: 'Server'):
        self.bot = server.bot
        self.server = server

        self.start_tasks()

    def start_tasks(self):
        self.manage_violations.start()

    async def new_violation(self, v: Violation):
        await v.save()
        await v.initial_notice()
        return v

    async def get_violation(self, violation_id: int, /):
        v = await ViolationModel.get_violation(violation_id)
        return Violation.load(self.server, v)

    async def get_violations(self, member: 'HeliosMember'):
        violations = await ViolationModel.get_violations(member)
        return [Violation.load(self.server, x) for x in violations]

    @tasks.loop(seconds=30)
    async def manage_violations(self):
        q = ViolationModel.select().where(ViolationModel.server_id == self.server.db_id,
                                          ViolationModel.state != ViolationStates.Paid.value)
        violations = await objects.prefetch(q, MemberModel.select())

        for violation in violations:
            violation = Violation.load(self.server, violation)
            if violation.past_due() and violation.state == ViolationStates.New:
                await violation.late_notice()
            elif violation.past_final_notice() and violation.state == ViolationStates.Due:
                await violation.final_notice()

    @manage_violations.before_loop
    async def manage_violations_before(self):
        await self.bot.wait_until_ready()


class Case:
    def __init__(self):
        ...
