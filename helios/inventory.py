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
from enum import member
from typing import TYPE_CHECKING, Union

from .items import Item
from .database import InventoryModel

if TYPE_CHECKING:
    from .member import HeliosMember

class Inventory:
    def __init__(self, member: 'HeliosMember'):
        self.member = member
        self.items = []

        self._model = None
        self._unsaved = True

    async def add_item(self, item: Item, quantity: int = 1):
        try:
            cur = self.items.index(item)
            self.items[cur].quantity += quantity
        except ValueError:
            item = item.copy(quantity)
            self.items.append(item)
        await self.save()

    async def remove_item(self, name: Union[str, Item], quantity: int = 1):
        if isinstance(name, Item):
            cur = self.items.index(name)
            self.items[cur].quantity -= quantity
            if self.items[cur].quantity <= 0:
                self.items.remove(self.items[cur])
        else:
            for item in self.items:
                if item.name == name:
                    item.quantity -= quantity
                    if item.quantity <= 0:
                        self.items.remove(item)
                    break
        await self.save()

    def to_dict(self):
        return {
            'member_id': self.member.id,
            'items': [item.to_dict() for item in self.items]
        }

    @classmethod
    def from_dict(cls, member: 'HeliosMember', data: Union[dict, InventoryModel]):
        if member.id != data['member_id']:
            raise ValueError('Member ID does not match')
        items = [Item.from_dict(item) for item in data['items']]
        c = cls(member)
        c.items = items
        if isinstance(data, InventoryModel):
            c._model = data
            c._unsaved = False
        return c

    async def save(self):
        if self._unsaved:
            if self._model:
                self._model.async_update(**self.to_dict())
                self._unsaved = False
            else:
                self._model = await InventoryModel.create(**self.to_dict())
                self._unsaved = False


    @classmethod
    async def load(cls, member: 'HeliosMember'):
        model = await InventoryModel.get(member.id)
        if model is None:
            return cls(member)
        return cls.from_dict(member, model)