from typing import Optional, TYPE_CHECKING

import discord

from .horses.enumerations import BetType
from .modals import BetModal
from .types import HeliosChannel

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .horses.race import EventRace


async def send_bad_response(interaction: discord.Interaction, message: str):
    embed = discord.Embed(
        colour=discord.Colour.red(),
        title='Something went wrong',
        description=message
    )
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        interaction.response.send_message(embed=embed, ephemeral=True)


class TopicView(discord.ui.View):
    def __init__(self, bot: 'HeliosBot'):
        super().__init__(timeout=None)
        self.bot = bot

    def get_channel(self, guild_id: int, channel_id: int) -> Optional['HeliosChannel']:
        server = self.bot.servers.get(guild_id)
        if server:
            channel = server.channels.get(channel_id)
            return channel
        return None

    @discord.ui.button(label='Save', style=discord.ButtonStyle.green, custom_id='topic:save')
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.get_channel(interaction.guild_id, interaction.channel_id)
        if not channel:
            await send_bad_response(interaction, 'This channel is no longer managed.')
            return
        if channel.channel_type != 'topic':
            await send_bad_response(interaction, 'This should not be possible')
            return
        await channel.save_channel(interaction=interaction)
        await channel.save()


class PreRaceView(discord.ui.View):
    def __init__(self, er: 'EventRace'):
        super().__init__(timeout=er.time_until_race.seconds)
        self.race = er

    def check_race_status(self):
        if self.race.phase == 1:
            self.bet.disabled = False
            self.show_bets.disabled = False
        else:
            self.bet.disabled = True
            self.show_bets.disabled = True

    @discord.ui.button(label='Bet', style=discord.ButtonStyle.blurple, disabled=True)
    async def bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self.race.stadium.server.members.get(interaction.user.id)
        await interaction.response.send_modal(BetModal(self.race, member))  # Modal handles all further actions

    @discord.ui.button(label='Show Bets', style=discord.ButtonStyle.green, disabled=True)
    async def show_bets(self, interaction: discord.Interaction, button: discord.ui.Button):
        bets = list(filter(lambda x: x.better_id == interaction.user.id, self.race.bets))
        if len(bets) == 0:
            await interaction.response.send_message('You have not placed any bets', ephemeral=True)
            return
        win = list(filter(lambda x: x.type == BetType.win, bets))
        place = list(filter(lambda x: x.type == BetType.place, bets))
        show = list(filter(lambda x: x.type == BetType.show, bets))
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f'{self.race.name} Personal Bets',
            description='All of your bets on this race.'
        )
        win_value = ''
        for bet in win:
            win_value += f'{self.race.stadium.horses[bet.horse_id].name} - **{bet.amount:,}**\n'
        embed.add_field(name='Win Bets', value=win_value if win_value else 'None')
        place_value = ''
        for bet in place:
            place_value += f'{self.race.stadium.horses[bet.horse_id].name} - **{bet.amount:,}**\n'
        embed.add_field(name='Place Bets', value=place_value if place_value else 'None')
        show_value = ''
        for bet in show:
            show_value += f'{self.race.stadium.horses[bet.horse_id].name} - **{bet.amount:,}**\n'
        embed.add_field(name='Show Bets', value=show_value if show_value else 'None')
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Register', style=discord.ButtonStyle.gray, disabled=True)
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show register view, wait for its completion, fill values
        member = self.race.stadium.server.members.get(interaction.user.id)
        horses = list(filter(lambda x: self.race.is_qualified(x), member.horses.values()))
        horse_strings = []
        for i, h in enumerate(horses):
            horse_strings.append(f'{i}. {h.name}')
        # TODO: Call register view


class YesNoView(discord.ui.View):
    def __init__(self, author: discord.Member, *, timeout=5):
        super().__init__(timeout=timeout)
        self.author = author
        self.value = None

    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.author:
            self.value = True
            await interaction.response.defer()
            self.stop()
        else:
            await interaction.response.send_message('You are not allowed to respond', ephemeral=True)

    @discord.ui.button(label='No', style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.author:
            self.value = False
            await interaction.response.defer()
            self.stop()
        else:
            await interaction.response.send_message('You are not allowed to respond', ephemeral=True)
