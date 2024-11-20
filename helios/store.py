#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
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
import datetime
from typing import TYPE_CHECKING

from .items import StoreItem

if TYPE_CHECKING:
    from .server import Server

class Store:
    def __init__(self, server:  'Server'):
        self.server = server
        self.items: list['StoreItem'] = []
        self.next_refresh = datetime.datetime.now(datetime.timezone.utc)

    def to_dict(self):
        return {
            'items': [item.to_dict() for item in self.items],
            'next_refresh': self.next_refresh,
        }

    @classmethod
    def from_dict(cls, server: 'Server', data: dict):
        store = cls(server)
        for item_data in data['items']:
            store.add_item(StoreItem.from_dict(item_data))
        store.next_refresh = data['next_refresh']
        return store

    def add_item(self, item: 'StoreItem'):
        self.items.append(item)

    def remove_item(self, item: 'StoreItem'):
        self.items.remove(item)
