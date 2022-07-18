from .stats import StatContainer, Stat
from .breed import Breed
from ..abc import HasSettings
from ..tools.settings import Settings


class Horse(HasSettings):
    _default_settings = {
        'tier': 1,
        'age': 0,
        'breed': None
    }

    def __init__(self):
        self.name = 'Unnamed'
        self.breed = Breed('')
        self.stats = StatContainer()
        self.stats['speed'] = Stat('speed', 0)
        self.stats['acceleration'] = Stat('acceleration', 0)
        self.stats['stamina'] = Stat('stamina', 0)
        self.settings = Settings(self._default_settings)

