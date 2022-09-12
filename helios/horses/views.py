from datetime import datetime
from fractions import Fraction
from typing import TYPE_CHECKING, Dict

import discord

from .enumerations import BetType
from .modals import SetBidModal
from ..modals import BetModal

if TYPE_CHECKING:
    from .race import Race
    from .horse import Horse
    from .auction import HorseListing, GroupAuction


class PreRaceView(discord.ui.View):
    def __init__(self, er: 'Race'):
        super().__init__(timeout=er.time_until_race.seconds)
        self.race = er
        if self.race.settings['type'] == 'basic':
            self.remove_item(self.register)

    def check_race_status(self):
        if self.race.phase == 1:
            self.register.disabled = True
            self.bet.disabled = False
            self.show_bets.disabled = False
            self.decimals.disabled = False
        else:
            self.register.disabled = False
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
        # Show register _view, wait for its completion, fill values
        member = self.race.stadium.server.members.get(interaction.user.id)
        horses = {}
        for key, horse in member.horses.items():
            if self.race.is_qualified(horse):
                horses[key] = horse
        if len(horses) < 1:
            await interaction.response.send_message(
                'You do not currently have any qualifying horses.',
                ephemeral=True
            )
            return
        view = HorsePickerView(self.race, horses)
        content = (f'Entry Cost: **{self.race.stake:,}**\n'
                   f'Your Points: **{member.points:,}**')
        message = await interaction.response.send_message(content, view=view,
                                                          ephemeral=True)
        await view.wait()
        horse = view.horse
        if horse is None:
            return
        if self.race.slots_left() < 1:
            await interaction.edit_original_response(content='All slots have '
                                                             'been filled',
                                                     view=None)
            return
        if member.points < self.race.stake:
            await interaction.edit_original_response(
                content=f'You need **{self.race.stake:,}** '
                        f'points to register in this race.',
                view=None
            )
            return
        member.points -= self.race.stake
        await member.save()
        await self.race.add_horse(horse)
        await self.race.update_embed()
        await interaction.edit_original_response(content=f'{horse.name} added '
                                                         f'to race!',
                                                 view=None)

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


class HorsePickerView(discord.ui.View):
    def __init__(self, race: 'Race', horses: Dict[int, 'Horse']):
        self.race = race
        self.horses = horses
        self.horse = None
        options = []
        for key, horse in self.horses.items():
            if len(options) < 25:
                options.append(discord.SelectOption(label=horse.name,
                                                    value=str(key)))
        super().__init__(timeout=race.time_until_betting.total_seconds())
        self.select_horse.options = options

    @discord.ui.select(placeholder='Pick a horse')
    async def select_horse(self, interaction: discord.Interaction,
                           select: discord.SelectMenu):
        val = int(self.select_horse.values[0])
        self.horse = self.horses.get(val)
        await interaction.response.defer()
        self.stop()


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
            await interaction.response.send_message(
                (f'The bid has already been increased to **{next_amount:,}**, '
                 f'try again. Consider using set bet if this keeps happening'),
                ephemeral=True
            )
        elif member.points < self.bid_amount:
            await interaction.response.send_message(
                f'You do not have the available funds!',
                ephemeral=True
            )
        elif not self.listing.can_bid(member, self.bid_amount):
            await interaction.response.send_message(
                f'You have achieved the maximum allowed horses.',
                ephemeral=True
            )
        else:
            await interaction.response.defer()
            highest = self.listing.get_highest_bidder()
            if highest.bidder_id != member.id:
                other = self.server.members.get(highest.bidder_id)
                if other:
                    await other.member.send(f'{interaction.user.name} has '
                                            'outbid you on '
                                            f'{self.listing.horse.name}!')
            self.listing.bid(member, self.bid_amount)

    @discord.ui.button(label='Set Bid', style=discord.ButtonStyle.gray)
    async def set_bid(self, interaction: discord.Interaction,
                      button: discord.Button):
        member = self.server.members.get(interaction.user.id)
        modal = SetBidModal(self.listing, member)
        await interaction.response.send_modal(modal)


class GroupAuctionView(discord.ui.View):
    def __init__(self, auction: 'GroupAuction', *, page=0):
        now = datetime.now().astimezone()
        delta = auction.end_time - now
        super().__init__(timeout=delta.total_seconds())
        self.auction = auction
        if auction.pages > 1:
            page_num = 25*page
            listings = self.auction[page_num:25+page_num]
        else:
            listings = self.auction.listings
        options = []
        for i, listing in enumerate(listings, start=1):
            option = discord.SelectOption(label=listing.horse.name,
                                          value=str(listing.horse_id),
                                          description=f'ID: {i:03}')
            options.append(option)
        self.select_horse.options = options

    @discord.ui.select()
    async def select_horse(self, interaction: discord.Interaction,
                           select: discord.ui.Select):
        selected_horse = int(select.values[0])
        listing = discord.utils.find(lambda x: x.horse_id == selected_horse,
                                     self.auction.listings)
        try:
            message = await interaction.user.send(embed=discord.Embed(
                title='Building Listing'
            ))
            listing.update_list.append(message)
            listing.new_bid = True
            await interaction.response.send_message(f'{message.jump_url}',
                                                    ephemeral=True)
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                'Sorry, I could not send you a DM.',
                ephemeral=True
            )

    async def select_page(self, interaction: discord.Interaction,
                          select: discord.SelectMenu):
        ...
