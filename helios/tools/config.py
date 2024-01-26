#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

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
        self.db_path = 'helios.db'
        self.db_host = 'http://127.0.0.1:8000/'
        self.db_port = '8000'
        self.db_username = 'admin'
        self.db_password = '123'

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
            'randomname_api_key': self.randomname_api_key,
            'db_path': self.db_path,
            'db_host': self.db_host,
            'db_port': self.db_port,
            'db_username': self.db_username,
            'db_password': self.db_password
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

