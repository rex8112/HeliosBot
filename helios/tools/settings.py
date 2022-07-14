class Settings:
    def __init__(self, data: dict):
        for k, v in data.items():
            if self.__getattribute__(k):
                raise AttributeError(f'Attribute {k} already exists')
            self.__setattr__(k, v)

    def to_dict(self) -> dict:
        d = dict()
        for k, v in self.__dict__.items():
            try:
                new_value = v.serialize()
            except AttributeError:
                new_value = v
            d[k] = new_value
        return d
