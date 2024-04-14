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

from typing import Callable, TYPE_CHECKING, Awaitable, Optional

import discord

from .effects import MuteEffect, DeafenEffect, ShieldEffect, DeflectorEffect, ChannelShieldEffect
from .views import TempMuteView, TempDeafenView, DurationView, YesNoView

if TYPE_CHECKING:
    from .server import Server
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

    @shop_item('Deflector')
    async def shop_deflector(self: ShopItem, member: 'HeliosMember', interaction: discord.Interaction):
        """Deflect a mute or deafen effect back to sender."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        if member.is_shielded():
            embed = discord.Embed(
                title='Shielded',
                description='You are already shielded from effects.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        server = self.shop.bot.servers.get(interaction.guild_id)  # type: Server
        cost = server.settings.deflector_points_per_hour.value
        view = YesNoView(member.member, timeout=30)
        embed = discord.Embed(
            title='Deflector',
            description=f'Are you sure you want to purchase the deflector for up to one hour for {cost}?',
            colour=discord.Colour.blurple()
        )

        message: discord.WebhookMessage = await interaction.followup.send(embed=embed, view=view)
        if await view.wait():
            embed = discord.Embed(
                title='Timed out',
                colour=discord.Colour.red()
            )
            await message.edit(embed=embed, view=None)
            return 0

        if not view.value:
            embed = discord.Embed(
                title='Cancelled',
                colour=discord.Colour.red()
            )
            await message.edit(embed=embed, view=None)
            return 0
        if member.points < cost:
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
        effect = DeflectorEffect(member, 60 * 60, cost=cost)
        await server.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        return cost

    @shop_item('Channel Shield')
    async def shop_channel_shield(self: ShopItem, member: 'HeliosMember', interaction: discord.Interaction):
        """Shield your channel from all effects for a period of time."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        channel = member.member.voice.channel if member.member.voice else None
        if channel is None:
            embed = discord.Embed(
                title='Not in Voice',
                description='You must be in a voice channel to purchase this item.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        channel = member.server.channels.dynamic_voice.channels.get(channel.id)
        if channel is None:
            embed = discord.Embed(
                title='Not in Dynamic Voice',
                description='You must be in a dynamic voice channel to purchase this item.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        if channel.has_effect('ChannelShieldEffect'):
            embed = discord.Embed(
                title='Shielded',
                description='This channel is already shielded from effects.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        server = self.shop.bot.servers.get(interaction.guild_id)  # type: Server
        cost = server.settings.channel_shield_points_per_hour.value
        view = DurationView(member, [('1 Hour', 1), ('2 Hours', 2), ('3 Hours', 3),
                                     ('4 Hours', 4), ('5 Hours', 5)],
                            cost, 'Hour(s)')
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
        if member.points < view.get_cost():
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
        effect = ChannelShieldEffect(channel, view.selected_time * 60 * 60, cost=view.get_cost())
        await channel.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        return view.get_cost()

    @shop_item('Shield')
    async def shop_shield(self: ShopItem, member: 'HeliosMember', interaction: discord.Interaction):
        """Shield yourself from all effects for a period of time."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        if member.is_shielded():
            embed = discord.Embed(
                title='Shielded',
                description='You are already shielded from effects.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        server = self.shop.bot.servers.get(interaction.guild_id)  # type: Server
        cost = server.settings.shield_points_per_hour.value
        view = DurationView(member, [('1 Hour', 1), ('2 Hours', 2), ('3 Hours', 3),
                                     ('4 Hours', 4), ('5 Hours', 5)],
                            cost, 'Hour(s)')
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
        if member.points < view.get_cost():
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
        effect = ShieldEffect(member, view.selected_time * 60 * 60, cost=view.get_cost())
        await server.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        return view.get_cost()

    @shop_item('Mute')
    async def shop_mute(self: ShopItem, member: 'HeliosMember', interaction: discord.Interaction):
        """Server mute someone who is in a voice channel for an amount of time."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        if member.is_shielded():
            embed = discord.Embed(
                title='Shielded',
                description='You are currently shielded from effects.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        if member.member.voice is None:
            embed = discord.Embed(
                title='Not in Voice',
                description='You must be in a voice channel to purchase this item.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        server = self.shop.bot.servers.get(interaction.guild_id)
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
        selected_member = server.members.get(view.selected_member.id)
        effect = MuteEffect(selected_member, view.selected_seconds, cost=view.value, muter=member,
                            reason=f'{member.member.name} temp muted for {view.selected_seconds} seconds.')
        await server.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        return view.value

    @shop_item('Deafen')
    async def shop_deafen(self: ShopItem, member: 'HeliosMember', interaction: discord.Interaction):
        """Server deafen someone who is in a voice channel for an amount of time."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        if member.is_shielded():
            embed = discord.Embed(
                title='Shielded',
                description='You are currently shielded from effects.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        if member.member.voice is None:
            embed = discord.Embed(
                title='Not in Voice',
                description='You must be in a voice channel to purchase this item.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return 0
        server = self.shop.bot.servers.get(interaction.guild_id)
        view = TempDeafenView(member)
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
        selected_member = server.members.get(view.selected_member.id)
        effect = DeafenEffect(selected_member, view.selected_seconds, cost=view.value, deafener=member,
                              reason=f'{member.member.name} temp deafened for {view.selected_seconds} seconds.')
        await server.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        return view.value
