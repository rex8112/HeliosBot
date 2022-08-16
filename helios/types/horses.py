from typing import TypedDict, Optional, Literal, Tuple

from .settings import SettingsSerializable

MaxRaceHorses = Literal[6, 12, 20]
RaceTypes = Literal['basic', 'maiden', 'stake', 'listed', 'grade3', 'grade2',
                    'grade1']


class HorseSerializable(TypedDict):
    server: int
    id: Optional[int]
    name: str
    breed: str
    stats: dict[str, str]
    born: Tuple[str, str]
    settings: SettingsSerializable


class StadiumSerializable(TypedDict):
    server: int
    day: int
    settings: dict
    events: list
