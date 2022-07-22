from typing import TypedDict, TYPE_CHECKING, Optional, Union, Dict, Tuple

if TYPE_CHECKING:
    from ..member import HeliosMember


Primitives = Union[int, float, bool, str]
ItemSerializable = Tuple[str, Primitives]
SettingsSerializable = Dict[str, Union[ItemSerializable, Primitives]]


class HorseSettings(TypedDict):
    breed: str
    gender: str
    age: int
    owner: Optional['HeliosMember']
    wins: int
