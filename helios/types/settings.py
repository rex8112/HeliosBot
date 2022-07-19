from typing import TypedDict, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..member import HeliosMember


class HorseSettings(TypedDict):
    breed: str
    tier: int
    gender: str
    age: int
    owner: Optional['HeliosMember']
