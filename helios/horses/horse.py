import random
from typing import TYPE_CHECKING, Optional

from .breed import Breed
from .stats import StatContainer, Stat
from ..abc import HasSettings
from ..tools.settings import Settings
from ..types.settings import HorseSettings

if TYPE_CHECKING:
    from ..member import HeliosMember


class Horse(HasSettings):
    _default_settings: HorseSettings = {
        'tier': 1,
        'gender': 'male',
        'age': 0,
        'breed': Breed(''),
        'owner': None
    }

    def __init__(self, tier: int, breed: str):
        self.name = 'Unknown'
        self.breed = Breed(breed)
        self.stats = StatContainer()
        self.stats['speed'] = Stat('speed', 0)
        self.stats['acceleration'] = Stat('acceleration', 0)
        self.stats['stamina'] = Stat('stamina', 0)
        self.settings: HorseSettings = self._default_settings.copy()
        self.settings.tier = tier

    @property
    def speed(self):
        return self.get_calculated_stat('speed')

    @property
    def acceleration(self):
        return self.get_calculated_stat('acceleration')

    @property
    def stamina(self):
        return self.get_calculated_stat('stamina')

    @classmethod
    def new(cls, name: str, breed: str, tier: int, owner: Optional['HeliosMember']):
        horse = cls(tier, breed)
        horse.name = name
        horse.settings['owner'] = owner
        horse.generate_stats()
        return horse

    def get_calculated_stat(self, stat: str):
        return (self.stats[stat].value + ((self.settings['tier'] - 1) * 10)) * self.breed.stat_multiplier[stat]

    def generate_stats(self):
        rand_speed = random.randint(1, 10)
        rand_accel = random.randint(1, 10)
        rand_stamina = random.randint(1, 10)
        self.stats['speed'].value = rand_speed
        self.stats['acceleration'].value = rand_accel
        self.stats['stamina'].value = rand_stamina
