import random
from typing import TYPE_CHECKING, Optional

from .breed import Breed
from .stats import StatContainer, Stat
from ..abc import HasSettings
from ..types.settings import HorseSettings
from ..types.horses import HorseSerializable
from ..tools.settings import Item

if TYPE_CHECKING:
    from ..member import HeliosMember


class Horse(HasSettings):
    _default_settings: HorseSettings = {
        'tier': 1,
        'gender': 'male',
        'age': 0,
        'owner': None,
        'wins': 0
    }

    def __init__(self, tier: int, breed: str):
        self._id = 0
        self.name = 'Unknown'
        self.breed = Breed(breed)
        self.stats = StatContainer()
        self.stats['speed'] = Stat('speed', 0)
        self.stats['acceleration'] = Stat('acceleration', 0)
        self.stats['stamina'] = Stat('stamina', 0)
        self.settings: HorseSettings = self._default_settings.copy()
        self.settings['tier'] = tier

        self._new = True
        self._changed = False

    @property
    def tier(self) -> int:
        return self.settings['tier']

    @property
    def speed(self) -> float:
        return self.get_calculated_stat('speed')

    @property
    def acceleration(self) -> float:
        return self.get_calculated_stat('acceleration')

    @property
    def stamina(self) -> float:
        return self.get_calculated_stat('stamina')

    @property
    def quality(self) -> float:
        total = 0
        quantity = 0
        for v in self.stats.stats.values():
            total += v.value
            quantity += 1
        return round(total / quantity, 2)

    @classmethod
    def new(cls, name: str, breed: str, tier: int, owner: Optional['HeliosMember']):
        horse = cls(tier, breed)
        horse.name = name
        horse.settings['owner'] = owner
        horse.generate_stats()
        return horse

    def get_calculated_stat(self, stat: str):
        return (self.stats[stat].value + ((self.tier - 1) * 10)) * self.breed.stat_multiplier[stat]

    def generate_stats(self):
        rand_speed = random.randint(1, 10)
        rand_accel = random.randint(1, 10)
        rand_stamina = random.randint(1, 10)
        self.stats['speed'].value = rand_speed
        self.stats['acceleration'].value = rand_accel
        self.stats['stamina'].value = rand_stamina

    def serialize(self) -> HorseSerializable:
        data: HorseSerializable = {
            'id': self._id,
            'name': self.name,
            'breed': self.breed.name,
            'stats': self.stats.serialize(),
            'settings': Item.serialize_dict(self.settings)
        }
        if self._new:
            data['id'] = None
        return data

    def _deserialize(self, data: HorseSerializable):
        self._id = data['id']
        self.name = data['name']
        self.breed = Breed(data['breed'])
        self.stats = StatContainer.from_dict(data['stats'])
        self.settings = Item.deserialize_dict(data['settings'])
        self._new = False
