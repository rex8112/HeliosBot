from typing import TypedDict, TYPE_CHECKING, Optional, Literal

from .settings import SettingsSerializable


MaxRaceHorses = Literal[6, 12]


class HorseSerializable(TypedDict):
    id: Optional[int]
    name: str
    breed: str
    stats: dict[str, str]
    settings: SettingsSerializable
