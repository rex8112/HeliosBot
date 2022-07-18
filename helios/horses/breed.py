breed_multipliers = {
    'unknown': {
        'speed': 1,
        'acceleration': 1,
        'stamina': 1
    }
}


class Breed:
    def __init__(self, name: str):
        self.name = name if name else 'unknown'
        self.stat_multiplier: dict[str, float] = breed_multipliers[self.name]
