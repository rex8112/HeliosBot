class Stat:
    def __init__(self, name: str, value: int):
        self.name = name
        self.value = value

    def __int__(self):
        return self.value

    def __str__(self):
        return f'{self.name}: {self.value}'

    @classmethod
    def from_dict(cls, d: dict):
        return cls(d['name'], d['value'])

    def serialize(self):
        return {
            'name': self.name,
            'value': self.value
        }


class StatContainer:
    def __init__(self, stats: dict[str, Stat] = None):
        if stats is None:
            stats = {}
        self.stats: dict[str, Stat] = stats

    def __setitem__(self, key, value):
        return self.stats.__setitem__(key, value)

    def __getitem__(self, item):
        return self.stats.__getitem__(item)

    @classmethod
    def from_dict(cls, d: dict):
        nd: dict[str, Stat] = dict()
        for k, v in d.items():
            if isinstance(v, dict):
                nd[k] = Stat.from_dict(v)
            elif isinstance(v, Stat):
                nd[k] = v
            else:
                raise NotImplemented
        return cls(nd)

    def get(self, index, default=None):
        return self.stats.get(index, default=default)

    def serialize(self):
        data = {}
        for k, v in self.stats.items():
            data[k] = v.serialize()
        return data

