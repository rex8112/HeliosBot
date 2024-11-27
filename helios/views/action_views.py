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
import math
from types import MethodType
from typing import TYPE_CHECKING, Optional

import discord

from ..colour import Colour
from ..effects import MuteEffect, DeafenEffect, ShieldEffect, ChannelShieldEffect

if TYPE_CHECKING:
    from ..helios_bot import HeliosBot
    from ..member import HeliosMember
    from ..server import Server


__all__ = ('ActionView', 'TempMuteActionView')


class ActionView(discord.ui.View):
    """A view for the action shop."""
    def __init__(self, bot: 'HeliosBot'):
        super().__init__(timeout=None)
        self.bot = bot

    def get_embed(self, server: 'Server') -> discord.Embed:
        embed = discord.Embed(
            title=f'{server.name} Action Shop',
            colour=Colour.actions(),
            description='Use action tokens to perform actions.')
        embed.add_field(name='Mute', value='Mute a user for a set amount of time.')
        embed.add_field(name='Deafen', value='Deafen a user for a set amount of time.')
        embed.add_field(name='Shield', value='Protect yourself from harmful actions.')
        embed.add_field(name='Channel Shield', value='Protect a voice channel from harmful actions.')
        return embed

    @discord.ui.button(label='Mute', style=discord.ButtonStyle.grey, custom_id='helios:action:shop:mute')
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        await interaction.response.defer(ephemeral=True, thinking=True)

        view = TempMuteActionView(member)
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

        embed = discord.Embed(
            title='Purchased!',
            colour=discord.Colour.green()
        )
        selected_member = server.members.get(view.selected_member.id)
        effect = MuteEffect(selected_member, view.selected_seconds, cost=view.value, muter=member,
                            reason=f'{member.member.name} temp muted for {view.selected_seconds} seconds.')
        await self.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        items = member.inventory.get_items('mute_token')
        if items:
            await member.inventory.remove_item(items[0], view.get_value())

    @discord.ui.button(label='Deafen', style=discord.ButtonStyle.grey, custom_id='helios:action:shop:deafen')
    async def deafen_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        await interaction.response.defer(ephemeral=True, thinking=True)

        view = TempDeafenActionView(member)
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

        embed = discord.Embed(
            title='Purchased!',
            colour=discord.Colour.green()
        )
        selected_member = server.members.get(view.selected_member.id)
        effect = DeafenEffect(selected_member, view.selected_seconds, cost=view.value, deafener=member,
                              reason=f'{member.member.name} temp deafened for {view.selected_seconds} seconds.')
        await self.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        items = member.inventory.get_items('deafen_token')
        if items:
            await member.inventory.remove_item(items[0], view.get_value())

    @discord.ui.button(label='Shield', style=discord.ButtonStyle.grey, custom_id='helios:action:shop:shield')
    async def shield_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        if member.is_shielded():
            embed = discord.Embed(
                title='Already Shielded',
                description='You are already shielded.',
                colour=discord.Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        view = DurationView(member, options=[('1h', 1), ('2h', 2), ('3h', 3), ('4h', 4), ('5h', 5)],
                            price_per_time=1, time_label='Hours', item_name='shield', item_display_name='Shields')
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

        embed = discord.Embed(
            title='Purchased!',
            colour=discord.Colour.green()
        )
        effect = ShieldEffect(member, view.selected_time * 3600, cost=view.get_cost())
        await self.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        items = member.inventory.get_items('shield')
        if items:
            await member.inventory.remove_item(items[0], view.get_cost())

    @discord.ui.button(label='Channel Shield', style=discord.ButtonStyle.grey, custom_id='helios:action:shop:bubble')
    async def bubble_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        await interaction.response.defer(ephemeral=True, thinking=True)

        channel = member.member.voice.channel if member.member.voice else None
        if channel is None:
            embed = discord.Embed(
                title='Not in Voice',
                description='You must be in a voice channel to purchase this item.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return
        channel = member.server.channels.dynamic_voice.channels.get(channel.id)
        if channel is None:
            embed = discord.Embed(
                title='Not in Dynamic Voice',
                description='You must be in a dynamic voice channel to purchase this item.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return
        if channel.has_effect('bubble'):
            embed = discord.Embed(
                title='Already Shielded',
                description='This channel is already shielded.',
                colour=discord.Colour.red()
            )
            await interaction.followup.send(embed=embed)
            return

        view = DurationView(member, options=[('1h', 1), ('2h', 2), ('3h', 3), ('4h', 4), ('5h', 5)],
                            price_per_time=1, time_label='Hours', item_name='bubble', item_display_name='Channel Shields')
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

        embed = discord.Embed(
            title='Purchased!',
            colour=discord.Colour.green()
        )

        effect = ChannelShieldEffect(channel, view.selected_time * 3600, cost=view.get_cost())
        await self.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        items = member.inventory.get_items('bubble')
        if items:
            await member.inventory.remove_item(items[0], view.get_cost())


class TempMuteActionView(discord.ui.View):
    item_name = 'mute_token'

    def __init__(self, author: 'HeliosMember'):
        super().__init__(timeout=180)
        self.author = author
        self.store = author.server.store
        self.selected_member: Optional['HeliosMember'] = None
        self.selected_seconds: int = 15
        self.value = 0
        self.confirmed = False
        self.error_message: str = ''

        self.item = self.store.get_item(self.item_name)

    def get_value(self):
        return math.ceil(self.selected_seconds / 15)

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title='Temp Mute',
            colour=Colour.error() if self.error_message else Colour.choice(),
            description=self.error_message
        )
        embed.add_field(name='Target',
                        value=f'{self.selected_member.member.display_name if self.selected_member else "None"}')
        embed.add_field(name='Duration', value=f'{self.selected_seconds} Seconds')
        embed.add_field(name='Price', value=f'{self.value} Tokens')
        embed.set_footer(text=f'Your Tokens: {self.author_tokens()}')
        if self.selected_member:
            embed.set_thumbnail(url=self.selected_member.member.display_avatar.url)
        return embed

    async def reload_message(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()
        self.value = self.get_value()
        await self.verify_member()
        embed = self.get_embed()
        self.reload_buttons()
        await interaction.edit_original_response(embed=embed, view=self)

    def author_tokens(self):
        items = self.author.inventory.get_items(self.item_name)
        if items:
            return items[0].quantity
        return 0

    def reload_buttons(self):
        if self.error_message:
            self.confirm_button.disabled = True
        else:
            self.confirm_button.disabled = False
        if self.value > self.author_tokens() or self.item.quantity < self.value - self.author_tokens():
            self.buy_remaining_button.disabled = False
        else:
            self.buy_remaining_button.disabled = True

    async def verify_member(self):
        member: 'HeliosMember' = self.selected_member
        if member is None:
            self.error_message = 'You must select someone first.'
            return False
        if self.author.is_shielded():
            self.error_message = 'You are shielded.'
            return False
        if self.author.member.voice is None:
            self.error_message = 'You are not in a voice channel.'
            return False
        if member.is_noob():
            self.error_message = f'{member.member.display_name} is still too new to be muted.'
            return False
        if member.member.voice is None or not member.member.voice.channel.permissions_for(self.author.member).view_channel:
            self.error_message = f'{member.member.display_name} is not in a voice channel.'
            return False
        if member.member.voice.mute:
            self.error_message = f'{member.member.display_name} is already muted.'
            return False
        if member == self.author.server.me:
            self.error_message = f'You can not mute me.'
            return False
        if member.is_shielded():
            self.error_message = f'{member.member.display_name} is shielded.'
            return False
        if self.value > self.author_tokens():
            self.error_message = f'You do not have enough tokens, you need {self.value}.'
            return False
        # if member.member.top_role > member.member.guild.me.top_role or member.member.guild.owner == member.member:
        #     self.error_message = f'I am sorry, I could not mute {member.member.display_name} even if I wanted to.'
        #     self.selected_member = None
        #     return False
        self.error_message = ''
        return True

    @discord.ui.select(cls=discord.ui.UserSelect, row=0)
    async def member_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        member: discord.Member = select.values[0]
        member: 'HeliosMember' = self.author.server.members.get(member.id)
        self.selected_member = member
        await self.reload_message(interaction)

    @discord.ui.button(label='15s', style=discord.ButtonStyle.grey, row=1)
    async def second_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 15
        await self.reload_message(interaction)

    @discord.ui.button(label='30s', style=discord.ButtonStyle.grey, row=1)
    async def third_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 30
        await self.reload_message(interaction)

    @discord.ui.button(label='45s', style=discord.ButtonStyle.grey, row=1)
    async def fourth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 45
        await self.reload_message(interaction)

    @discord.ui.button(label='60s', style=discord.ButtonStyle.grey, row=1)
    async def fifth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 60
        await self.reload_message(interaction)

    @discord.ui.button(label='Purchase', style=discord.ButtonStyle.green, disabled=True, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        if self.selected_member is None:
            await interaction.response.send_message(content='You must select someone first.', ephemeral=True)
            return
        if not await self.verify_member():
            await self.reload_message(interaction)
            return
        await interaction.response.defer()
        self.confirmed = True
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label='Refresh', style=discord.ButtonStyle.blurple, row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        await self.reload_message(interaction)

    @discord.ui.button(label='Buy Remaining', style=discord.ButtonStyle.red, row=2)
    async def buy_remaining_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        if self.value <= 0:
            await interaction.response.send_message(content='You have nothing to buy.', ephemeral=True)
            return
        needed = self.value - self.author_tokens()
        if self.item.quantity < needed:
            await interaction.response.send_message(content='Not enough tokens in shop.', ephemeral=True)
            return
        item_value = self.item.price * needed
        if item_value > self.author.points:
            await interaction.response.send_message(content=f'You do not have enough {self.author.server.points_name}.', ephemeral=True)
            return
        await interaction.response.defer()
        await self.store.purchase(self.item, self.author, needed)
        await self.reload_message(interaction)

class TempDeafenActionView(TempMuteActionView):
    item_name = 'deafen_token'

    def get_embed(self) -> discord.Embed:
        embed = super().get_embed()
        embed.title = 'Temp Deafen'
        return embed

    async def verify_member(self):
        member: 'HeliosMember' = self.selected_member
        if member is None:
            self.error_message = 'You must select someone first.'
            return False
        if self.author.is_shielded():
            self.error_message = 'You are shielded.'
            return False
        if self.author.member.voice is None:
            self.error_message = 'You are not in a voice channel.'
            return False
        if member.is_noob():
            self.error_message = f'{member.member.display_name} is still too new to be deafened.'
            return False
        if not member.member.voice or not member.member.voice.channel.permissions_for(self.author.member).view_channel:
            self.error_message = f'{member.member.display_name} is not in a voice channel.'
            return False
        if member.member.voice.deaf:
            self.error_message = f'{member.member.display_name} is already deafened.'
            return False
        if member == self.author.server.me:
            self.error_message = f'You can not deafen me, that would be a waste. I\'m not programmed to hear you.'
            return False
        if member.is_shielded():
            self.error_message = f'{member.member.display_name} is shielded.'
            return False
        if self.value > self.author_tokens():
            self.error_message = f'You do not have enough tokens, you need {self.value}.'
            return False
        self.error_message = ''
        return True

class DurationView(discord.ui.View):
    def __init__(self, author: 'HeliosMember', options: list[tuple[str, int]] = None, *, price_per_time: int = 1,
                 time_label: str = 'Seconds', item_name: str, item_display_name: str):
        super().__init__(timeout=180)
        self.author = author
        self.store = author.server.store
        self.selected_time: int = 1
        self.confirmed = False
        self.error_message: str = ''
        self.options = options or [('5s', 5), ('15s', 15), ('30s', 30), ('45s', 45), ('60s', 60)]
        self.time_label = time_label
        self.item_name = item_name
        self.item_display_name = item_display_name
        self.item = self.store.get_item(item_name)
        self.price_per_second = price_per_time
        self.build_buttons()

    def get_cost(self):
        return self.selected_time * self.price_per_second

    def get_item_count(self):
        items = self.author.inventory.get_items(self.item_name)
        if items:
            return items[0].quantity
        return 0

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title='Duration',
            colour=discord.Colour.blurple(),
            description=self.error_message
        )
        embed.add_field(name='Duration', value=f'{self.selected_time:,} {self.time_label}')
        embed.add_field(name='Price', value=f'{self.get_cost()} {self.item_display_name}')
        embed.set_footer(text=f'Your {self.item_display_name}: {self.get_item_count()}')
        return embed

    async def reload_message(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = self.get_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    def make_callback(self, seconds: int):
        async def callback(_: discord.ui.Button, interaction: discord.Interaction):
            self.selected_time = seconds
            await self.reload_message(interaction)
        return callback

    def build_buttons(self):
        for label, seconds in self.options:
            button = discord.ui.Button(
                style=discord.ButtonStyle.grey,
                label=label
            )
            button.callback = MethodType(self.make_callback(seconds), button)
            self.add_item(button)

    @discord.ui.button(label='Purchase', style=discord.ButtonStyle.green, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        await interaction.response.defer()
        self.confirmed = True
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label='Buy Remaining', style=discord.ButtonStyle.red, row=2)
    async def buy_remaining_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        if self.get_cost() <= 0:
            await interaction.response.send_message(content='You have nothing to buy.', ephemeral=True)
            return
        needed = self.get_cost() - self.get_item_count()
        if self.item.quantity < needed:
            await interaction.response.send_message(content='Not enough tokens in shop.', ephemeral=True)
            return
        item_value = self.item.price * needed
        if item_value > self.author.points:
            await interaction.response.send_message(content=f'You do not have enough {self.author.server.points_name}.', ephemeral=True)
            return
        await interaction.response.defer()
        await self.store.purchase(self.item, self.author, needed)
        await self.reload_message(interaction)

