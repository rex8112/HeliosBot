from datetime import datetime
from fractions import Fraction
from typing import TYPE_CHECKING

import discord

from .enumerations import BetType
from ..modals import BetModal

if TYPE_CHECKING:
    from .race import Race
    from .auction import HorseListing, GroupAuction


class PreRaceView(discord.ui.View):
    def __init__(self, er: 'Race'):
        super().__init__(timeout=er.time_until_race.seconds)
        self.race = er

    def check_race_status(self):
        if self.race.phase == 1:
            self.bet.disabled = False
            self.show_bets.disabled = False
            self.decimals.disabled = False
        else:
            self.bet.disabled = True
            self.show_bets.disabled = True
            self.decimals.disabled = True

    @discord.ui.button(label='Bet', style=discord.ButtonStyle.blurple,
                       disabled=True)
    async def bet(self, interaction: discord.Interaction,
                  button: discord.ui.Button):
        member = self.race.stadium.server.members.get(interaction.user.id)
        await interaction.response.send_modal(
            BetModal(self.race, member))  # Modal handles all further actions

    @discord.ui.button(label='Show Bets', style=discord.ButtonStyle.green,
                       disabled=True)
    async def show_bets(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        bets = list(filter(lambda x: x.better_id == interaction.user.id,
                           self.race.bets))
        if len(bets) == 0:
            await interaction.response.send_message(
                'You have not placed any bets', ephemeral=True)
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
            win_value += (f'{self.race.stadium.horses[bet.horse_id].name} - '
                          f'**{bet.amount:,}**\n')
        embed.add_field(name='Win Bets',
                        value=win_value if win_value else 'None')
        place_value = ''
        for bet in place:
            place_value += (f'{self.race.stadium.horses[bet.horse_id].name} - '
                            f'**{bet.amount:,}**\n')
        embed.add_field(name='Place Bets',
                        value=place_value if place_value else 'None')
        show_value = ''
        for bet in show:
            show_value += (f'{self.race.stadium.horses[bet.horse_id].name} - '
                           f'**{bet.amount:,}**\n')
        embed.add_field(name='Show Bets',
                        value=show_value if show_value else 'None')
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Register', style=discord.ButtonStyle.gray,
                       disabled=True)
    async def register(self, interaction: discord.Interaction,
                       button: discord.ui.Button):
        # Show register view, wait for its completion, fill values
        member = self.race.stadium.server.members.get(interaction.user.id)
        horses = list(filter(lambda x: self.race.is_qualified(x),
                             member.horses.values()))
        horse_strings = []
        for i, h in enumerate(horses):
            horse_strings.append(f'{i}. {h.name}')
        # TODO: Call register view

    @discord.ui.button(label='Math is Hard', style=discord.ButtonStyle.red,
                       disabled=True, row=1)
    async def decimals(self, interaction: discord.Interaction,
                       button: discord.Button):
        desc = ''
        for h in self.race.horses:
            odds = self.race.calculate_odds(h)
            fraction = Fraction(odds).limit_denominator(10)
            desc += (
                f'`{fraction.numerator:3} / {fraction.denominator:2} = '
                f'{int(fraction.numerator) / int(fraction.denominator):4.1f}` '
                f'{h.name}\n')
        embed = discord.Embed(
            colour=discord.Colour.red(),
            title=self.race.name,
            description=desc
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ListingView(discord.ui.View):
    # noinspection PyTypeChecker
    def __init__(self, listing: 'HorseListing'):
        self.server = listing.auction.stadium.server
        self.listing = listing
        self.bid_amount = self.next_amount

        now = datetime.now().astimezone()
        time_left = listing.end_time - now
        super().__init__(timeout=time_left.total_seconds())

        button: discord.Button = next(
            filter(lambda x: x.label.startswith('Bid'),
                   self.children)
        )
        button.label = f'Bid {self.bid_amount}'

    @property
    def next_amount(self):
        if len(self.listing.bids) > 0:
            return self.listing.get_highest_bidder().amount + 100
        else:
            return self.listing.settings['min_bid']

    @discord.ui.button(label='Bid', style=discord.ButtonStyle.green)
    async def bid(self, interaction: discord.Interaction,
                  button: discord.Button):
        member = self.server.members.get(interaction.user.id)
        next_amount = self.next_amount - 100
        if self.bid_amount <= next_amount:
            await interaction.response.send(
                (f'The bid has already been increased to **{next_amount:,}**, '
                 f'try again. Consider using set bet if this keeps happening'),
                ephemeral=True
            )
        else:
            await interaction.response.defer()
            self.listing.bid(member, self.bid_amount)

    @discord.ui.button(label='Set Bid', style=discord.ButtonStyle.gray)
    async def set_bid(self, interaction: discord.Interaction,
                      button: discord.Button):
        member = self.server.members.get(interaction.user.id)
        #  await interaction.response.send_modal()


class GroupAuctionView(discord.ui.View):
    def __init__(self, auction: 'GroupAuction'):
        now = datetime.now().astimezone()
        delta = auction.end_time - now
        super().__init__(timeout=delta.total_seconds())
        self.auction = auction

    async def select_horse(self, interaction: discord.Interaction,
                           select: discord.SelectMenu):
        ...

    async def select_page(self, interaction: discord.Interaction,
                          select: discord.SelectMenu):
        ...
