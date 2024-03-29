from typing import Callable, TYPE_CHECKING, Awaitable, Optional

import discord

from .views import TempMuteView

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .member import HeliosMember


class ShopItem:
    def __init__(self, name: str, desc: str, callback: Callable[['ShopItem', 'HeliosMember', discord.Interaction], Awaitable[int]]):
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

    def decorator(func: Callable[['ShopItem', 'HeliosMember', discord.Interaction], Awaitable[int]]):
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

    def get_names(self) -> list[str]:
        names = []
        for item in self.items:
            names.append(item.name)
        return names

    def get_item(self, name: str) -> Optional['ShopItem']:
        for item in self.items:
            if item.name == name:
                return item
            return None

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
    async def shop_mute(self: ShopItem, member: 'HeliosMember', interaction: discord.Interaction):
        """Price: variable
        Server mute someone who is in a voice channel for an amount of time."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        # server = self.shop.bot.servers.get(interaction.guild_id)
        view = TempMuteView(member)
        embed = view.get_embed()

        message: discord.WebhookMessage = await interaction.followup.send(embed=embed, view=view)
        if await view.wait():
            embed = discord.Embed(
                title='Timed out',
                colour=discord.Colour.red()
            )
            await message.edit(embed=embed, view=None)
            return 0

        if not view.confirmed:
            embed = discord.Embed(
                title='Cancelled',
                colour=discord.Colour.red()
            )
            await message.edit(embed=embed, view=None)
            return 0
        if member.points < view.value:
            embed = discord.Embed(
                title=f'Not Enough {member.server.points_name.capitalize()}',
                colour=discord.Colour.red()
            )
            await message.edit(embed=embed, view=None)
            return 0

        embed = discord.Embed(
            title='Purchased!',
            colour=discord.Colour.green()
        )
        if not await view.selected_member.temp_mute(view.selected_seconds, member, view.value):
            embed = discord.Embed(
                title='Something Went Wrong',
                colour=discord.Colour.red(),
                description='Sorry, I could not mute this person.'
            )
            await message.edit(embed=embed, view=None)
            return 0
        await message.edit(embed=embed, view=None)
        return view.value
