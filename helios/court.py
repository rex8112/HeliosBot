from discord.ext import tasks
from typing import TYPE_CHECKING, overload

from .database import ViolationModel, objects
from .enums import ViolationStates
from .violation import Violation

if TYPE_CHECKING:
    from .server import Server


class Court:
    def __init__(self, server: 'Server'):
        self.bot = server.bot
        self.server = server

        self.start_tasks()

    def start_tasks(self):
        self.manage_violations.start()

    async def get_violation(self, violation_id: int, /):
        v = await objects.get(ViolationModel, id=violation_id)
        return Violation.load(self.server, v)

    @tasks.loop(seconds=30)
    async def manage_violations(self):
        q = ViolationModel.select().where(ViolationModel.server_id == self.server.db_id,
                                          ViolationModel.state != ViolationStates.Paid.value)
        violations = await objects.prefetch(q)

        for violation in violations:
            violation = Violation.load(self.server, violation)
            if violation.past_due() and violation.state == ViolationStates.New:
                await violation.late_notice()
            elif violation.past_final_notice() and violation.state == ViolationStates.Due:
                await violation.final_notice()

    @manage_violations.before_loop
    async def manage_violations_before(self):
        await self.bot.wait_until_ready()
