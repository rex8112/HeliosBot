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

__all__ = ('Item', 'Items', 'StoreItem', 'ItemDescriptions')

from typing import Literal


class Item:
    def __init__(self, name: str, quantity: int, display_name: str, data: dict = None):
        if data is None:
            data = {}

        self.name = name
        self.display_name = display_name
        self.quantity = quantity
        self.data = data

    def __eq__(self, o: object):
        if not isinstance(o, Item):
            return NotImplemented
        return self.name == o.name and self.data == o.data

    def __str__(self):
        return f'{self.display_name} x{self.quantity}'

    def __repr__(self):
        return f'Item<{self.name}, {self.quantity}, {self.display_name}, {bool(self.data)}>'

    def get_description(self):
        return ItemDescriptions.get_description(self)

    def copy(self, quantity: int = None):
        return Item(self.name, self.quantity if self.quantity is None else quantity, self.display_name, self.data.copy())

    def to_dict(self):
        return {
            'name': self.name,
            'quantity': self.quantity,
            'display_name': self.display_name,
            'data': self.data if self.data else {}
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['name'], data['quantity'], data['display_name'], data['data'])


class StoreItem(Item):
    """An item that can be bought from the store"""
    def __init__(self, name: str, quantity: int, display_name: str, price: int, max_price: int, min_price: int,
                 stock: int, max_stock: int, min_stock: int, data: dict = None):
        super().__init__(name, quantity, display_name, data)
        self.price = price
        self.stock = stock
        self.max_price = max_price
        self.min_price = min_price
        self.max_stock = max_stock
        self.min_stock = min_stock

    def to_dict(self):
        return {
            'name': self.name,
            'quantity': self.quantity,
            'display_name': self.display_name,
            'price': self.price,
            'max_price': self.max_price,
            'min_price': self.min_price,
            'stock': self.stock,
            'max_stock': self.max_stock,
            'min_stock': self.min_stock,
            'data': self.data if self.data else {}
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data['name'],
            quantity=data['quantity'],
            display_name=data['display_name'],
            price=data['price'],
            max_price=data['max_price'],
            min_price=data['min_price'],
            stock=data['stock'],
            max_stock=data['max_stock'],
            min_stock=data['min_stock'],
            data=data.get('data', {})
        )

    @classmethod
    def from_item(cls, item: Item, price: int, max_price: int, min_price: int, stock: int, max_stock: int, min_stock: int):
        return cls(item.name, item.quantity, item.display_name, price, max_price, min_price, stock, max_stock, min_stock, item.data)

    def to_item(self):
        """Convert the store item to a regular item"""
        return Item(self.name, self.quantity, self.display_name, self.data.copy())

    def set_to_max(self):
        self.stock = self.max_stock
        self.price = self.max_price

    def refresh(self):
        self.quantity = self.stock

    def __repr__(self):
        return f'StoreItem<{self.name}, {self.quantity}, {self.display_name}, {self.price:,}, {bool(self.data)}>'


class Items:
    @staticmethod
    def discount(discount: int, restrictions: list[str] = None):
        if restrictions is None:
            restrictions = []
        if len(restrictions) == 1:
            display_name = f'{restrictions[0].capitalize()} Discount {discount}% off'
        else:
            display_name = f'Store Discount {discount}% off'
        return Item('discount', 1, display_name, {'discount': discount,
                                                'restrictions': restrictions})
    @staticmethod
    def gamble_credit(credit: int):
        return Item('gamble_credit', 1, f'{credit:,} Gambling Credit', {'credit': credit})

    @staticmethod
    def mute_token():
        return Item('mute_token', 1, 'Mute Token')

    @staticmethod
    def deafen_token():
        return Item('deafen_token', 1, 'Deafen Token')

    @staticmethod
    def shield():
        return Item('shield', 1, 'Shield')

    @staticmethod
    def bubble():
        return Item('bubble', 1, 'Bubble')

    @staticmethod
    def deflector():
        return Item('deflector', 1, 'Deflector')

    @staticmethod
    def bj_powerup(action: Literal['surrender','show_dealer','show_next','perfect_card']):
        if action == 'surrender':
            return Item('bj_powerup', 1, 'Blackjack Powerup: Surrender', {'action': 'surrender'})
        elif action == 'show_dealer':
            return Item('bj_powerup', 1, 'Blackjack Powerup: Show Dealer Card', {'action': 'show_dealer'})
        elif action == 'show_next':
            return Item('bj_powerup', 1, 'Blackjack Powerup: Show Next Card', {'action': 'show_next'})
        elif action == 'perfect_card':
            return Item('bj_powerup', 1, 'Blackjack Powerup: Perfect Card', {'action': 'perfect_card'})
        else:
            raise ValueError('Invalid action')

class ItemDescriptions:
    @staticmethod
    def get_description(item: Item):
        func = getattr(ItemDescriptions, item.name, None)
        if func:
            return func(item)
        return 'No description available'

    @staticmethod
    def discount(item: Item):
        if item.data['restrictions']:
            return f'{item.data["discount"]}% off for {", ".join(item.data["restrictions"])}'
        else:
            return f'{item.data["discount"]}% off the shop.'

    @staticmethod
    def gamble_credit(item: Item):
        return f'{item.data["credit"]:,} Gambling Credit for the casino.'

    @staticmethod
    def mute_token(item: Item):
        return 'Allows muting a user for a limited time'

    @staticmethod
    def deafen_token(item: Item):
        return 'Allows deafening a user for a limited time'

    @staticmethod
    def shield(item: Item):
        return 'Protects the user from harmful effects for a limited time'

    @staticmethod
    def bubble(item: Item):
        return 'Protects an entire channel from harmful effects for a limited time'

    @staticmethod
    def deflector(item: Item):
        return 'Deflects one harmful effect for a limited time'