from typing import TypedDict, TYPE_CHECKING, Optional, Union, Dict, Tuple

if TYPE_CHECKING:
    from ..member import HeliosMember
    from .horses import MaxRaceHorses
    from discord import TextChannel, Message


Primitives = Union[int, float, bool, str]
ItemSerializable = Tuple[str, Primitives]
SettingsSerializable = Dict[str, Union[ItemSerializable, Primitives]]
PossibleSettings = Union['HorseSettings']


class HorseSettings(TypedDict):
    breed: str
    gender: str
    age: int
    owner: Optional['HeliosMember']
    wins: int


class EventRaceSettings(TypedDict):
    channel: Optional['TextChannel']
    message: Optional['Message']
    purse: int
    stake: int
    max_horses: 'MaxRaceHorses'
