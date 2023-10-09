import math
from typing import Callable, TYPE_CHECKING, Awaitable

import discord

from .tools.views import SelectMemberView, YesNoView
from .views import TempMuteView

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
        price = await self.callback(self, member, interaction)
        await member.add_points(-price, 'Helios', f'Shop Purchase: {self.name}')


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
        await interaction.response.defer()
        server = self.shop.bot.servers.get(interaction.guild_id)
        embed = discord.Embed(
            title='Mute',
            description='Choose someone in a voice chat to mute.',
            colour=discord.Colour.orange()
        )
        view = TempMuteView(member)

        message: discord.WebhookMessage = await interaction.followup.send(embed=embed, view=view)
        if await view.wait():
            await message.delete()

        if not view.confirmed:
            embed = discord.Embed(
                title='Cancelled',
                colour=discord.Colour.red()
            )
            await message.edit(embed=embed, view=None)
            await message.delete(delay=5)
            return 0
        if member.points < view.value:
            embed = discord.Embed(
                title='Not Enough Mins',
                colour=discord.Colour.red()
            )
            await message.edit(embed=embed, view=None)
            await message.delete(delay=5)
            return 0

        embed = discord.Embed(
            title='Purchased!',
            colour=discord.Colour.green()
        )
        await view.selected_member.temp_mute(view.selected_seconds)
        await message.edit(embed=embed, view=None)
        await message.delete(delay=5)
        return view.value