from typing import TypedDict, Optional, Literal

from .settings import SettingsSerializable

MaxRaceHorses = Literal[6, 12, 20]
RaceTypes = Literal['basic', 'maiden', 'daily', 'stake']


class HorseSerializable(TypedDict):
    server: int
    id: Optional[int]
    name: str
    breed: str
    stats: dict[str, str]
    born: str
    settings: SettingsSerializable


class StadiumSerializable(TypedDict):
    server: int
    day: int
    settings: dict
