import math
from types import MethodType
from typing import Optional, TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ..server import Server
    from ..member import HeliosMember

__all__ = ('ShopView', 'TempMuteView')


class ShopView(discord.ui.View):
    def __init__(self, server: 'Server'):
        super().__init__(timeout=None)
        self.bot = server.bot
        self.shop = server.shop
        self.server = server
        self.make_buttons()

    def make_buttons(self):
        for item in self.shop.items:
            async def callback(s: discord.ui.Button, interaction: discord.Interaction):
                author = self.server.members.get(interaction.user.id)
                await item.purchase(author, interaction)
            button = discord.ui.Button(
                style=discord.ButtonStyle.grey,
                label=item.name,
                custom_id=f'helios:{self.server.id}:shop:{item.name.lower().replace(" ", "")}'
            )
            button.callback = MethodType(callback, button)
            self.add_item(button)


class TempMuteView(discord.ui.View):
    PRICE_PER_SECOND = 1

    def __init__(self, author: 'HeliosMember'):
        super().__init__(timeout=180)
        self.author = author
        self.selected_member: Optional['HeliosMember'] = None
        self.selected_seconds: int = 5
        self.value = 0
        self.confirmed = False
        self.error_message: str = ''

    async def get_value(self):
        if not self.selected_member:
            return 0
        seconds = await self.selected_member.get_point_mute_duration()
        value = 0
        for _ in range(self.selected_seconds):
            tier = int(seconds // 30)
            value += int(self.PRICE_PER_SECOND * math.pow(2, tier))
            seconds += 1
        return value

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title='Temp Mute',
            colour=discord.Colour.blurple(),
            description=self.error_message
        )
        embed.add_field(name='Target',
                        value=f'{self.selected_member.member.display_name if self.selected_member else "None"}')
        embed.add_field(name='Duration', value=f'{self.selected_seconds} Seconds')
        embed.add_field(name='Price', value=f'{self.value} {self.author.server.points_name.capitalize()}')
        embed.set_footer(text=f'Your {self.author.server.points_name.capitalize()}: {self.author.points}')
        if self.selected_member:
            embed.set_thumbnail(url=self.selected_member.member.display_avatar.url)
        return embed

    async def reload_message(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.value = await self.get_value()
        embed = self.get_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    async def verify_member(self, member: discord.Member):
        member: 'HeliosMember' = self.author.server.members.get(member.id)
        if member.is_noob():
            self.error_message = f'{member.member.display_name} is still too new to be muted.'
            self.selected_member = None
            return False
        if not member.member.voice:
            self.error_message = f'{member.member.display_name} is not in a voice channel.'
            self.selected_member = None
            return False
        if member.member.voice.mute:
            self.error_message = f'{member.member.display_name} is already muted.'
            self.selected_member = None
            return False
        # if member.member.top_role > member.member.guild.me.top_role or member.member.guild.owner == member.member:
        #     self.error_message = f'I am sorry, I could not mute {member.member.display_name} even if I wanted to.'
        #     self.selected_member = None
        #     return False
        return True

    @discord.ui.select(cls=discord.ui.UserSelect, row=0)
    async def member_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        member: discord.Member = select.values[0]
        if not await self.verify_member(member):
            await self.reload_message(interaction)
            return
        member: 'HeliosMember' = self.author.server.members.get(member.id)
        self.selected_member = member
        self.error_message = ''
        await self.reload_message(interaction)

    @discord.ui.button(label='5s', style=discord.ButtonStyle.grey, row=1)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 5
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

    @discord.ui.button(label='Purchase', style=discord.ButtonStyle.green, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        if not await self.verify_member(self.selected_member.member):
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
