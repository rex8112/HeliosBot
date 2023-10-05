from typing import Callable, TYPE_CHECKING, Awaitable

import discord

from .tools.views import SelectMemberView

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .member import HeliosMember


class ShopItem:
    def __init__(self, name: str, desc: str, callback: Callable[['HeliosMember', discord.Interaction], Awaitable[int]]):
        self.name = name
        self.desc = desc
        self.shop = None
        self.callback = callback

    def set_shop(self, shop: 'Shop'):
        self.shop = shop

    async def purchase(self, member: 'HeliosMember', interaction: discord.Interaction):
        price = await self.callback(member, interaction)
        await member.add_points(price, f'Shop Purchased: {self.name}')


def shop_item(name: str, /):
    if callable(name):
        raise TypeError('item decorator must be called not referenced.')

    def decorator(func: Callable[['HeliosMember'], Awaitable[int]]):
        return ShopItem(name, func.__doc__, func)
    return decorator


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

    @shop_item('Mute')
    async def shop_mute(self, member: 'HeliosMember', interaction: discord.Interaction):
        """Price: variable
        Server mute someone who is in a voice channel for an amount of time."""
        def check(mem: discord.Member):
            if mem.voice is None:
                return False, f'{mem.display_name} is not in a voice channel.'
            if mem.voice.mute:
                return False, f'{mem.display_name} is already muted.'
            return True, ''

        await interaction.response.defer()
        embed = discord.Embed(
            title='Mute',
            description='Choose someone in a voice chat to mute.',
            colour=discord.Colour.orange()
        )
        view = SelectMemberView(member.member, check=check)
        if interaction:
            await interaction.response.send_message(embed=embed, view=view)
        else:
            await member.member.send(embed=embed, view=view)
        await view.wait()

        members = view.selected
        if len(members) < 1:
            await interaction.response.edit_message('Cancelled/Timed Out', embed=None, view=None)
            return 0

        member = members[0]
        # TODO: Need to get how many times recently they've been muted.
