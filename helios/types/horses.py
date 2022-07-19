from typing import TypedDict, TYPE_CHECKING, Optional

from .settings import SettingsSerializable


class HorseSerializable(TypedDict):
    id: Optional[int]
    name: str
    breed: str
    stats: dict[str, str]
    settings: SettingsSerializable
