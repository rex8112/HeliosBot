from typing import TYPE_CHECKING, Optional

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

    def __init__(self, user: 'HeliosMember', victim: 'HeliosMember', v_type: ViolationTypes, description: str,
                 paid: bool):
        self.user = user
        self.victim = victim
        self.type = v_type
        self.description = description
        self.paid = paid

        self._db_entry = None

    def to_dict(self):
        return {
            'user_id': self.user.db_id,
            'victim_id': self.victim.db_id,
            'paid': self.paid,
            'type': self.type.value,
            'description': self.description
        }

    @classmethod
    async def from_db_entry(cls, server: 'Server', db_entry: ViolationModel):
        user = server.members.get(db_entry.user.member_id)
        victim = server.members.get(db_entry.victim.member_id)
        v = cls(user, victim, ViolationTypes(db_entry.type), db_entry.description, db_entry.paid)
        return v

    @classmethod
    async def new(cls, user: 'HeliosMember', victim: 'HeliosMember', v_type: ViolationTypes, description: str):
        v = cls(user, victim, v_type, description, False)
        v._db_entry = await objects.create(ViolationModel, **v.to_dict())
        return v

    @classmethod
    async def new_shop(cls, user: 'HeliosMember', victim: 'HeliosMember', description: str):
        return cls.new(user, victim, ViolationTypes.Shop, description)
