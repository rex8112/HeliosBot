import datetime
from typing import TYPE_CHECKING, Optional

import discord
from discord.utils import format_dt

from .colour import Colour
from .database import ViolationModel, objects
from .member import HeliosMember
from .enums import ViolationTypes

if TYPE_CHECKING:
    from .server import Server
    from .member import HeliosMember


class Violation:
    _db_entry: Optional['ViolationModel']
    paid: bool
    description: str
    type: ViolationTypes
    victim: HeliosMember
    user: HeliosMember

    def __init__(self, user: 'HeliosMember', victim: 'HeliosMember', v_type: ViolationTypes, cost: int, description: str,
                 paid: bool, due_date: datetime.datetime = None):
        self.user = user
        self.victim = victim
        self.type = v_type
        self.description = description
        self.cost = cost
        self.paid = paid
        self.due_date = due_date if due_date else (datetime.datetime.now(datetime.timezone.utc)
                                                   + datetime.timedelta(days=7))

        self._db_entry = None

    @property
    def created_on(self) -> Optional[datetime.datetime]:
        return self._db_entry.created_on if self._db_entry else None

    def to_dict(self):
        return {
            'user_id': self.user.db_id,
            'victim_id': self.victim.db_id,
            'paid': self.paid,
            'type': self.type.value,
            'cost': self.cost,
            'due_date': self.due_date,
            'description': self.description
        }

    def is_new(self):
        return self._db_entry is None

    async def save(self):
        if self.is_new():
            self._db_entry = await objects.create(ViolationModel, **self.to_dict())
        else:
            await objects.update(self._db_entry, **self.to_dict())

    @classmethod
    async def load(cls, server: 'Server', db_entry: ViolationModel):
        user = server.members.get(db_entry.user.member_id)
        victim = server.members.get(db_entry.victim.member_id)
        v = cls(user, victim, ViolationTypes(db_entry.type), db_entry.cost, db_entry.description, db_entry.paid, db_entry.due_date)
        return v

    @classmethod
    def new(cls, user: 'HeliosMember', victim: 'HeliosMember', v_type: ViolationTypes, cost: int, description: str):
        v = cls(user, victim, v_type, cost, description, False)
        return v

    @classmethod
    def new_shop(cls, user: 'HeliosMember', victim: 'HeliosMember', cost, description: str):
        return cls.new(user, victim, ViolationTypes.Shop, cost, description)

    async def pay(self) -> bool:
        if self.user.points < self.cost:
            return False

        if self.victim is None or self.victim == self.user.server.me:
            await self.user.add_points(-self.cost, 'Helios', f'{self.type.name} Violation: {self.description}')
        else:
            await self.user.transfer_points(self.victim, self.cost,
                                            f'{self.type.name} Violation: {self.description}',
                                            f'{self.type.name} Violation Settlement')

        await self.save()
        return True

    async def initial_notice(self):
        embed = discord.Embed(
            title=f'{self.type.name} Violation!',
            colour=Colour.violation(),
            description=self.description
        )
        embed.add_field(name='Fine Amount', value=f'{self.cost} {self.user.server.points_name.capitalize()}')
        embed.add_field(name='Due Date', value=f'{format_dt(self.due_date)}\n{format_dt(self.due_date, "R")}')
        await self.user.member.send(embed=embed)

    async def late_notice(self):
        embed = discord.Embed(
            title=f'{self.type.name} Violation Fee Past Due',
            colour=Colour.violation(),
            description=f'Your previous violation is past due. Please pay the fine immediately!'
        )
        embed.add_field(name='Violation Description', value=self.description, inline=False)
        embed.add_field(name='Fine Amount', value=f'{self.cost} {self.user.server.points_name.capitalize()}')
        embed.add_field(name='Due Date', value=f'{format_dt(self.due_date)}\n{format_dt(self.due_date, "R")}')
        await self.user.member.send(embed=embed)

    async def final_notice(self):
        embed = discord.Embed(
            title=f'{self.type.name} Violation Fee Final Notice',
            colour=Colour.violation(),
            description=f'Your previous violation is past due. Please pay the fine immediately! '
                        f'**This is your final notice!**'
        )
        embed.add_field(name='Violation Description', value=self.description, inline=False)
        embed.add_field(name='Fine Amount', value=f'{self.cost} {self.user.server.points_name.capitalize()}')
        embed.add_field(name='Due Date', value=f'{format_dt(self.due_date)}\n{format_dt(self.due_date, "R")}')
        await self.user.member.send(embed=embed)
