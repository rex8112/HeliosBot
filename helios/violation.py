from typing import TYPE_CHECKING

from .member import HeliosMember
from .enums import ViolationTypes

if TYPE_CHECKING:
    from .member import HeliosMember


class Violation:
    description: str
    type: ViolationTypes
    victim: HeliosMember
    user: HeliosMember

    def __init__(self, user: 'HeliosMember', victim: 'HeliosMember', v_type: ViolationTypes, description: str):
        self.user = user
        self.victim = victim
        self.type = v_type
        self.description = description
