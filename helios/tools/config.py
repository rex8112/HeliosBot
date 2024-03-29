import json
from os.path import exists


class Config:
    def __init__(self) -> None:
        self.token = ''
        self.owner = '180067685986467840'
        self.api_url = 'http://127.0.0.1:8000/'
        self.file_path = 'config.json'
        self.api_username = 'admin'
        self.api_password = '123'
        self.randomname_api_key = 'asdfsdf'

    # Class Methods
    @classmethod
    def from_file_path(cls, path: str = 'config.json') -> 'Config':
        config = cls()
        config.file_path = path
        config.load()
        return config

    # Private Methods

    def _serialize(self, data: dict) -> None:
        data_str = json.dumps(data, indent=4, sort_keys=True)
        self.file = data_str

    def _deserialize(self) -> dict:
        data = {}
        try:
            data = json.loads(self.file)
        except json.decoder.JSONDecodeError:
            return {}
        return data

    # Methods

    def save(self):
        data = {
            'token': self.token,
            'owner': self.owner,
            'api_url': self.api_url,
            'api_username': self.api_username,
            'api_password': self.api_password,
            'randomname_api_key': self.randomname_api_key
        }
        self._serialize(data)

    def load(self):
        data = self._deserialize()
        if not data:
            self.save()
            return
        for key, value in data.items():
            self.__setattr__(key, value)

    @property
    def file(self) -> str:
        if exists(self.file_path):
            with open(self.file_path, 'r') as file:
                content = file.read()
                return content
        else:
            return '{}'

    @file.setter
    def file(self, content: str) -> None:
        with open(self.file_path, 'w+') as file:
            file.write(content)

