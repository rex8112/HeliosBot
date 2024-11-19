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
from typing import TYPE_CHECKING, Optional

import discord

from ..colour import Colour
from ..effects import MuteEffect, DeafenEffect

if TYPE_CHECKING:
    from ..member import HeliosMember
    from ..server import Server


__all__ = ('ActionView', 'TempMuteActionView')


class ActionView(discord.ui.View):
    def __init__(self, server: 'Server'):
        super().__init__(timeout=None)
        self.bot = server.bot
        self.server = server

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f'{self.server.name} Action Shop',
            colour=Colour.actions(),
            description='Use action tokens to perform actions.')
        embed.add_field(name='Mute', value='Mute a user for a set amount of time.')
        return embed

    @discord.ui.button(label='Mute', style=discord.ButtonStyle.grey, custom_id='helios:action:shop:mute')
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self.server.members.get(interaction.user.id)
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
        selected_member = self.server.members.get(view.selected_member.id)
        effect = MuteEffect(selected_member, view.selected_seconds, cost=view.value, muter=member,
                            reason=f'{member.member.name} temp muted for {view.selected_seconds} seconds.')
        await self.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        items = member.inventory.get_items('mute_token')
        if items:
            await member.inventory.remove_item(items[0], view.get_value())

    @discord.ui.button(label='Deafen', style=discord.ButtonStyle.grey, custom_id='helios:action:shop:deafen')
    async def deafen_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self.server.members.get(interaction.user.id)
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
        selected_member = self.server.members.get(view.selected_member.id)
        effect = DeafenEffect(selected_member, view.selected_seconds, cost=view.value, deafener=member,
                              reason=f'{member.member.name} temp deafened for {view.selected_seconds} seconds.')
        await self.bot.effects.add_effect(effect)
        await message.edit(embed=embed, view=None)
        items = member.inventory.get_items('deafen_token')
        if items:
            await member.inventory.remove_item(items[0], view.get_value())

class TempMuteActionView(discord.ui.View):
    def __init__(self, author: 'HeliosMember'):
        super().__init__(timeout=180)
        self.author = author
        self.selected_member: Optional['HeliosMember'] = None
        self.selected_seconds: int = 15
        self.value = 0
        self.confirmed = False
        self.error_message: str = ''

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
        await interaction.response.defer()
        self.value = self.get_value()
        await self.verify_member()
        embed = self.get_embed()
        self.reload_buttons()
        await interaction.edit_original_response(embed=embed, view=self)

    def author_tokens(self):
        items = self.author.inventory.get_items('mute_token')
        if items:
            return items[0].quantity
        return 0

    def reload_buttons(self):
        if self.error_message:
            self.confirm_button.disabled = True
        else:
            self.confirm_button.disabled = False

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

class TempDeafenActionView(TempMuteActionView):
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

    def author_tokens(self):
        items = self.author.inventory.get_items('deafen_token')
        if items:
            return items[0].quantity
        return 0
