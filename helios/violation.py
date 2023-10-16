import datetime
from typing import TYPE_CHECKING, Optional

import discord
from discord.utils import format_dt

from .colour import Colour
from .database import ViolationModel, objects
from .enums import ViolationTypes, ViolationStates
from .views import ViolationView

if TYPE_CHECKING:
    from .server import Server
    from .member import HeliosMember


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class Violation:
    _db_entry: Optional['ViolationModel']
    paid: bool
    description: str
    type: ViolationTypes
    victim: 'HeliosMember'
    user: 'HeliosMember'

    def __init__(self, user: 'HeliosMember', victim: 'HeliosMember', v_type: ViolationTypes, cost: int, description: str,
                 due_date: datetime.datetime = None):
        self.user = user
        self.victim = victim
        self.type = v_type
        self.description = description
        self.cost = cost
        self.due_date = due_date if due_date else (datetime.datetime.now(datetime.timezone.utc)
                                                   + datetime.timedelta(days=7))

        self.state = ViolationStates.New

        self._db_entry = None

    def __str__(self):
        return f'{self.type.name.capitalize()} Violation #{self.id}'

    def __hash__(self):
        return hash(f'helios.violation.{self.id}')

    @property
    def created_on(self) -> Optional[datetime.datetime]:
        return self._db_entry.created_on if self._db_entry else None

    @property
    def id(self):
        return self._db_entry.id

    @property
    def paid(self):
        return self.state == ViolationStates.Paid

    def to_dict(self):
        return {
            'server_id': self.user.server.db_id,
            'user_id': self.user.db_id,
            'victim_id': self.victim.db_id,
            'type': self.type.value,
            'state': self.state.value,
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
            self._db_entry.update_model_instance(self._db_entry, self.to_dict())
            await objects.update(self._db_entry)

    @classmethod
    def load(cls, server: 'Server', db_entry: ViolationModel):
        user = server.members.get(db_entry.user.member_id)
        victim = server.members.get(db_entry.victim.member_id)
        v = cls(user, victim, ViolationTypes(db_entry.type), db_entry.cost, db_entry.description, db_entry.due_date)
        v.state = ViolationStates(db_entry.state)
        v._db_entry = db_entry
        return v

    @classmethod
    def new_shop(cls, user: 'HeliosMember', victim: 'HeliosMember', cost: int, description: str):
        return cls(user, victim, ViolationTypes.Shop, cost, description)

    async def pay(self) -> bool:
        if self.user.points < self.cost:
            return False

        if self.victim is None or self.victim == self.user.server.me:
            await self.user.add_points(-self.cost, 'Helios', f'{self.type.name} Violation: {self.description}')
        else:
            await self.user.transfer_points(self.victim, self.cost,
                                            f'{self.type.name} Violation: {self.description}',
                                            f'{self.type.name} Violation Settlement')

        self.state = ViolationStates.Paid
        await self.save()
        return True

    def past_due(self):
        now = utc_now()
        return now > self.due_date

    def past_final_notice(self):
        now = utc_now()
        return now > self.due_date + datetime.timedelta(days=2)

    def get_paid_embed(self):
        embed = discord.Embed(
            title='Violation Paid!',
            colour=Colour.success(),
            description='You have paid your violation!'
        )
        return embed

    def get_info_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f'{self}',
            colour=Colour.violation(),
            description=self.description
        )
        embed.add_field(name='Fine Amount', value=f'{self.cost} {self.user.server.points_name.capitalize()}')
        embed.add_field(name='Due Date', value=f'{format_dt(self.due_date, "R")}\n\n{format_dt(self.due_date)}')
        return embed

    async def initial_notice(self):
        embed = discord.Embed(
            title=f'{self}',
            colour=Colour.violation(),
            description=self.description
        )
        embed.add_field(name='Fine Amount', value=f'{self.cost} {self.user.server.points_name.capitalize()}')
        embed.add_field(name='Due Date', value=f'{format_dt(self.due_date, "R")}\n\n{format_dt(self.due_date)}')
        await self.user.member.send(embed=embed, view=ViolationView(self.user.server, self._db_entry.id))

    async def late_notice(self):
        embed = discord.Embed(
            title=f'{self} Fee Past Due',
            colour=Colour.violation(),
            description=f'Your previous violation is past due. Please pay the fine immediately!'
        )
        embed.add_field(name='Violation Description', value=self.description, inline=False)
        embed.add_field(name='Fine Amount', value=f'{self.cost} {self.user.server.points_name.capitalize()}')
        embed.add_field(name='Due Date', value=f'{format_dt(self.due_date, "R")}\n\n{format_dt(self.due_date)}')
        await self.user.member.send(embed=embed, view=ViolationView(self.user.server, self._db_entry.id))
        self.state = ViolationStates.Due
        await self.save()

    async def final_notice(self):
        embed = discord.Embed(
            title=f'{self} Fee Final Notice',
            colour=Colour.violation(),
            description=f'Your previous violation is past due. Please pay the fine immediately! '
                        f'**This is your final notice!**'
        )
        embed.add_field(name='Violation Description', value=self.description, inline=False)
        embed.add_field(name='Fine Amount', value=f'{self.cost} {self.user.server.points_name.capitalize()}')
        embed.add_field(name='Due Date', value=f'{format_dt(self.due_date, "R")}\n\n{format_dt(self.due_date)}')
        await self.user.member.send(embed=embed, view=ViolationView(self.user.server, self._db_entry.id))
        self.state = ViolationStates.Illegal
        await self.save()
