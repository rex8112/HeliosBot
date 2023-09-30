from typing import Callable, TYPE_CHECKING, Awaitable

import discord

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .member import HeliosMember


class Shop:
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.items = self._get_items()

    def get_select_options(self) -> list[discord.SelectOption]:
        options = []
        for item in self.items:
            option = discord.SelectOption(label=item.name, description=item.desc)
            options.append(option)
        return options

    def _get_items(self) -> list['ShopItem']:
        items = []
        for attr_name in dir(self):
            if attr_name.startswith('__'):
                continue

            attr = getattr(self, attr_name)
            if isinstance(attr, ShopItem):
                attr.set_shop(self)
                items.append(attr)
        return items


def shop_item(name: str, /):
    if callable(name):
        raise TypeError('item decorator must be called not referenced.')

    def decorator(func: Callable[['HeliosMember'], Awaitable[int]]):
        return ShopItem(name, func.__doc__, func)
    return decorator


class ShopItem:
    def __init__(self, name: str, desc: str, callback: Callable[['HeliosMember'], Awaitable[int]]):
        self.name = name
        self.desc = desc
        self.shop = None
        self.callback = callback

    def set_shop(self, shop: 'Shop'):
        self.shop = shop

    async def purchase(self, member: 'HeliosMember'):
        price = await self.callback(member)
        await member.add_points(price, f'Shop Purchased: {self.name}')
