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

__all__ = ('Item', 'Items', 'MuteItem', 'StoreItem', 'ItemDescriptions')

from typing import Literal, TYPE_CHECKING

from .effects import MuteEffect, DeafenEffect

if TYPE_CHECKING:
    from .member import HeliosMember


class Item:
    """An item that can be used or stored in the inventory"""
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
        return Item(self.name, quantity if quantity is not None else self.quantity, self.display_name, self.data.copy())

    def to_dict(self):
        return {
            'name': self.name,
            'quantity': self.quantity,
            'display_name': self.display_name,
            'data': self.data if self.data else {}
        }

    async def verify(self, user: 'HeliosMember', target: 'HeliosMember', *args) -> tuple[bool, str]:
        """Verify if the item can be used
        :param user: The user using the item
        :param target: The target user
        :param args: The arguments passed to the item"""
        return True, ''

    async def use(self, user: 'HeliosMember', target: 'HeliosMember', *args) -> bool:
        """Use the item
        :param user: The user using the item
        :param target: The target user
        :param args: The arguments passed to the item"""
        verify = await self.verify(user, target, *args)
        return verify[0]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['name'], data['quantity'], data['display_name'], data['data'])


class MuteItem(Item):
    SECONDS_PER_TOKEN = 15

    def user_tokens(self, user: 'HeliosMember') -> int:
        """Get the number of tokens the user has"""
        return user.inventory.get_items(self.name)[0].quantity if user.inventory.get_items(self.name) else 0

    """An item that can be used to mute a user"""
    async def verify(self, user: 'HeliosMember', target: 'HeliosMember', *args) -> tuple[bool, str]:
        value = args[0] if args else 0
        if not isinstance(value, int):
            return False, 'Invalid value'

        if target is None:
            return False, 'You must select someone first.'
        if target.is_shielded():
            return False, 'You are shielded.'
        if user.member.voice is None:
            return False, 'You are not in a voice channel.'
        if not user.member.voice.channel.permissions_for(target.member).view_channel:
            return False, f'{target.member.display_name} can not see your channel.'
        if target.is_noob():
            return False, f'{target.member.display_name} is still too new to be muted.'
        if target.member.voice is None or not target.member.voice.channel.permissions_for(
                user.member).view_channel:
            return False, f'{target.member.display_name} is not in a voice channel.'
        if target.member.voice.mute:
            return False, f'{target.member.display_name} is already muted.'
        if target == target.server.me:
            return False, f'You can not mute me.'
        if target.is_shielded():
            return False, f'{target.member.display_name} is shielded.'
        if value <= 0:
            return False, 'You must select a value greater than 0.'
        if value > self.user_tokens(user):
            return False, f'You do not have enough tokens, you need {value}.'
        # if member.member.top_role > member.member.guild.me.top_role or member.member.guild.owner == member.member:
        #     self.error_message = f'I am sorry, I could not mute {member.member.display_name} even if I wanted to.'
        #     self.selected_member = None
        #     return False
        return True, ''

    async def use(self, user: 'HeliosMember', target: 'HeliosMember', *args) -> bool:
        verify = await self.verify(user, target, *args)
        if not verify[0]:
            return False

        value = args[0]

        effect = MuteEffect(target, self.SECONDS_PER_TOKEN * value, cost=value, muter=user,
                            reason=f'{target.member.name} temp muted for {self.SECONDS_PER_TOKEN * value} seconds.')
        await user.bot.effects.add_effect(effect)
        items = user.inventory.get_items('mute_token')
        if items:
            await user.inventory.remove_item(items[0], value)


class DeafenItem(Item):
    SECONDS_PER_TOKEN = 15

    def user_tokens(self, user: 'HeliosMember') -> int:
        """Get the number of tokens the user has"""
        return user.inventory.get_items(self.name)[0].quantity if user.inventory.get_items(self.name) else 0


    async def verify(self, user: 'HeliosMember', target: 'HeliosMember', *args) -> tuple[bool, str]:
        value = args[0] if args else 0
        if not isinstance(value, int):
            return False, 'Invalid value'

        if target is None:
            return False, 'You must select someone first.'
        if user.is_shielded():
            return False, 'You are shielded.'
        if user.member.voice is None:
            return False, 'You are not in a voice channel.'
        if not user.member.voice.channel.permissions_for(target.member).view_channel:
            return False, f'{target.member.display_name} can not see your channel.'
        if target.is_noob():
            return False, f'{target.member.display_name} is still too new to be deafened.'
        if not target.member.voice or not target.member.voice.channel.permissions_for(user.member).view_channel:
            return False, f'{target.member.display_name} is not in a voice channel.'
        if target.member.voice.deaf:
            return False, f'{target.member.display_name} is already deafened.'
        if target == user.server.me:
            return False, f'You can not deafen me, that would be a waste. I\'m not programmed to hear you.'
        if target.is_shielded():
            return False, f'{target.member.display_name} is shielded.'
        if value <= 0:
            return False, 'You must select a value greater than 0.'
        if value > self.user_tokens(user):
            return False, f'You do not have enough tokens, you need {value}.'
        return True, ''

    async def use(self, user: 'HeliosMember', target: 'HeliosMember', *args) -> bool:
        verify = await self.verify(user, target, *args)
        if not verify[0]:
            return False

        value = args[0]

        effect = DeafenEffect(target, self.SECONDS_PER_TOKEN * value, cost=value, deafener=user,
                            reason=f'{target.member.name} temp deafened for {self.SECONDS_PER_TOKEN * value} seconds.')
        await user.bot.effects.add_effect(effect)
        items = user.inventory.get_items('deafen_token')
        if items:
            await user.inventory.remove_item(items[0], value)



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
    def get_item_type(name: str):
        if name == 'mute_token':
            return MuteItem
        elif name == 'deafen_token':
            return DeafenItem
        return Item

    @staticmethod
    def get_from_dict(data: dict):
        cls = Items.get_item_type(data['name'])
        return cls.from_dict(data)

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
        return MuteItem('mute_token', 1, 'Mute Token')

    @staticmethod
    def deafen_token():
        return DeafenItem('deafen_token', 1, 'Deafen Token')

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

    @staticmethod
    def loot_crate(_type: Literal['common']):
        return Item('loot_crate', 1, 'Loot Crate', {'type': _type})

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

    @staticmethod
    def bj_powerup(item: Item):
        if item.data['action'] == 'surrender':
            return 'Allows surrendering a blackjack hand'
        elif item.data['action'] == 'show_dealer':
            return 'Allows showing the dealer\'s hidden card'
        elif item.data['action'] == 'show_next':
            return 'Allows showing the next card in the deck'
        elif item.data['action'] == 'perfect_card':
            return 'Allows drawing the perfect card for the situation. Will draw 11 if your hand is < 10'
        else:
            return 'No description available'