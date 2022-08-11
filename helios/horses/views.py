from typing import TYPE_CHECKING

import discord

from .enumerations import BetType
from ..modals import BetModal

if TYPE_CHECKING:
    from .race import EventRace


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