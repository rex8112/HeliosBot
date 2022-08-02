import datetime
import math
import random
from typing import TYPE_CHECKING, Optional

from .breed import Breed
from .stats import StatContainer, Stat
from ..abc import HasSettings
from ..exceptions import IdMismatchError
from ..tools.settings import Item
from ..types.horses import HorseSerializable
from ..types.settings import HorseSettings

if TYPE_CHECKING:
    from ..member import HeliosMember
    from ..stadium import Stadium


class Horse(HasSettings):
    _default_settings: HorseSettings = {
        'gender': 'male',
        'age': 0,
        'owner': None,
        'wins': 0
    }
    base_stat = 10

    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self._id = 0
        self.name = 'Unknown'
        self.breed = Breed('')
        self.date_born = datetime.datetime.now().astimezone().date()
        self.stats = StatContainer()
        self.stats['speed'] = Stat('speed', 0)
        self.stats['acceleration'] = Stat('acceleration', 0)
        self.settings: HorseSettings = self._default_settings.copy()

        self._new = True
        self._changed = False

    @property
    def id(self) -> int:
        return self._id

    @property
    def tier(self) -> int:
        return math.ceil(self.stats['speed'].value)

    @property
    def speed(self) -> float:
        return self.get_calculated_stat('speed')

    @property
    def acceleration(self) -> float:
        return self.get_calculated_stat('acceleration')

    @property
    def stamina(self) -> float:
        return self.breed.stat_multiplier['stamina'] * 500

    @property
    def quality(self) -> float:
        total = 0
        quantity = 0
        for v in self.stats.stats.values():
            total += v.value
            quantity += 1
        return round(total / quantity, 2)

    @classmethod
    def new(cls, name: str, breed: str, owner: Optional['HeliosMember'], *, num: int = None):
        horse = cls(breed)
        horse.name = name
        horse.settings['owner'] = owner
        horse.generate_stats(num=num)
        return horse

    @classmethod
    def from_dict(cls, stadium: 'Stadium', data: dict):
        h = cls(stadium)
        h._deserialize(data)
        return h

    def pay(self, amount: float):
        ...

    def get_calculated_stat(self, stat: str):
        return (Horse.base_stat + self.stats[stat].value) * self.breed.stat_multiplier[stat]

    def generate_stats(self, num=None):
        if not num:
            num = random.choices(
                range(1, 11),
                weights=(33, 20, 15, 10, 7, 5, 4, 3, 2, 1),
                k=1
            )[0]
        speed_diff = round(random.uniform(0, 0.5), 2)
        accel_diff = round(random.uniform(0, 0.5), 2)
        rand_speed = num - speed_diff
        rand_accel = num - accel_diff
        self.stats['speed'].value = rand_speed
        self.stats['acceleration'].value = rand_accel

    def serialize(self) -> HorseSerializable:
        data: HorseSerializable = {
            'server': self.stadium.server.id,
            'id': self._id,
            'name': self.name,
            'breed': self.breed.name,
            'stats': self.stats.serialize(),
            'born': Item.serialize(self.date_born),
            'settings': Item.serialize_dict(self.settings)
        }
        if self._new:
            data['id'] = None
        return data

    def _deserialize(self, data: HorseSerializable):
        if data['server'] != self.stadium.server.id:
            raise IdMismatchError('This horse does not belong to this stadium.')
        self._id = data['id']
        self.name = data['name']
        self.breed = Breed(data['breed'])
        self.stats = StatContainer.from_dict(data['stats'])
        self.date_born = Item.deserialize(data['born'])
        self.settings = Item.deserialize_dict(data['settings'], guild=self.stadium.guild)
        self._new = False