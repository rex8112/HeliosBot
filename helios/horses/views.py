from datetime import datetime
from fractions import Fraction
from typing import TYPE_CHECKING, Dict

import discord

from .enumerations import BetType
from .modals import SetBidModal, NameChangeModal
from ..modals import BetModal
from ..views import YesNoView

if TYPE_CHECKING:
    from ..member import HeliosMember
    from ..helios_bot import HeliosBot
    from .race import Race
    from .horse import Horse
    from .auction import HorseListing, GroupAuction


class PreRaceView(discord.ui.View):
    def __init__(self, er: 'Race'):
        super().__init__(timeout=er.time_until_race.seconds)
        self.race = er
        if self.race.settings['type'] == 'basic' or self.race.invite_only:
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
        owners = [h.owner for h in self.race.horses]
        if member in owners and self.race.is_restricted():
            await interaction.response.send_message(
                'You can only have one horse in a race.',
                ephemeral=True
            )
            return
        for key, horse in member.horses.items():
            if self.race.is_qualified(horse):
                horses[key] = horse
        if len(horses) < 1:
            await interaction.response.send_message(
                'You do not currently have any qualifying horses.',
                ephemeral=True
            )
            return
        view = RaceHorsePickerView(self.race, horses)
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
        if not self.race.is_qualified(horse):
            await interaction.edit_original_response(
                content='This horse is no longer qualified. This most likely '
                        'means that you already put this horse in a race.',
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
    def __init__(self, horses: Dict[int, 'Horse'], *,
                 min_horses=1, max_horses=1):
        self.horses = horses
        self.horses_selected = []
        options = []
        for key, horse in self.horses.items():
            if len(options) < 25:
                options.append(discord.SelectOption(label=horse.name,
                                                    value=str(key)))
        super().__init__(timeout=30)
        self.select_horse.min_values = min_horses
        self.select_horse.max_values = max_horses
        self.select_horse.options = options

    @discord.ui.select(placeholder='Pick a horse')
    async def select_horse(self, interaction: discord.Interaction,
                           select: discord.SelectMenu):
        for val in self.select_horse.values:
            horse = self.horses.get(int(val))
            if horse:
                self.horses_selected.append(horse)
        await interaction.response.defer()
        self.stop()


class RaceHorsePickerView(discord.ui.View):
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

        if (self.listing.settings['max_bid']
                and self.bid_amount >= self.listing.settings['max_bid']):
            self.bid_amount = self.listing.settings['max_bid']
            self.bid.label = f'Buy {self.bid_amount}'
        else:
            self.bid.label = f'Bid {self.bid_amount}'

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
                f'You only have **{member.points:,}** points!',
                ephemeral=True
            )
        elif not self.listing.can_bid(member, self.bid_amount):
            await interaction.response.send_message(
                f'You have achieved the maximum allowed horses.',
                ephemeral=True
            )
        else:
            await interaction.response.defer()
            if len(self.listing.bids) > 0:
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
            channel_ids = [x.channel.id for x in listing.update_list]
            dm_channel = interaction.user.dm_channel
            if dm_channel is None:
                dm_channel = await interaction.user.create_dm()
            if dm_channel.id in channel_ids:
                await interaction.response.send_message(
                    f'You already have a detailed listing in our DMs',
                    ephemeral=True
                )
                return
            if listing.cancelled:
                await interaction.response.send_message(
                    f'This listing was cancelled due to a bot issue, '
                    f'they should be resold tomorrow.',
                    ephemeral=True
                )
                return
            elif listing.done:
                winner = listing.get_highest_allowed_bid()
                if winner:
                    await interaction.response.send_message(
                        f'This listing is already over, <@{winner.bidder_id}> '
                        f'won the auction.',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'This listing is already over, no one bought the '
                        f'horse',
                        ephemeral=True
                    )
                return
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


class HorseOwnerView(discord.ui.View):
    def __init__(self, owner: 'HeliosMember', horse: 'Horse'):
        super().__init__(timeout=60)
        self.owner = owner
        self.horse = horse
        if not self.horse.is_maiden():
            self.change_name.disabled = True

    @discord.ui.button(label='Change Name', style=discord.ButtonStyle.gray)
    async def change_name(self, interaction: discord.Interaction,
                          button: discord.Button):
        if self.horse.is_maiden():
            await interaction.response.send_modal(NameChangeModal(self.horse))
        else:
            await interaction.response.send_message(f'{self.horse.name} can no'
                                                    f' longer have their name'
                                                    f' changed.',
                                                    ephemeral=True)

    @discord.ui.button(label='Sell', style=discord.ButtonStyle.red)
    async def sell_horse(self, interaction: discord.Interaction,
                         button: discord.Button):
        sell_price = int(self.horse.value * 0.25)
        view = YesNoView(self.owner.member, timeout=10)
        await interaction.response.send_message(f'Would you like to sell '
                                                f'**{self.horse.name}** for '
                                                f'**{sell_price:,}** points?',
                                                view=view,
                                                ephemeral=True)
        await view.wait()
        if view.value is None or view.value is False:
            try:
                await interaction.edit_original_response(view=None)
            except (discord.Forbidden, discord.HTTPException,
                    discord.NotFound):
                ...
            finally:
                return
        self.stop()
        self.horse.owner = None
        self.owner.points += sell_price
        await self.horse.save()
        await self.owner.save()
        await self.owner.member.send(f'You have sold **{self.horse.name}** '
                                     f'for **{sell_price:,}**!')


class SeasonRegistration(discord.ui.View):
    def __init__(self, bot: 'HeliosBot'):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='Register', style=discord.ButtonStyle.green,
                       custom_id='horseseasonregister')
    async def register(self, interaction: discord.Interaction,
                       button: discord.Button):
        stadium = self.bot.servers.get(interaction.guild_id).stadium
        member = stadium.server.members.get(interaction.user.id)
        horses = {}
        for key, horse in member.horses.items():
            if (stadium.check_qualification('listed', horse)
                    and not horse.get_flag('REGISTERED')):
                horses[key] = horse
        if len(horses) < 1:
            await interaction.response.send_message(
                'You do not have any registrable horses, they must be '
                'eligible to race in a listed race.',
                ephemeral=True
            )
            return
        horse_view = HorsePickerView(horses, max_horses=member.max_horses)
        await interaction.response.send_message(
            'Registration costs **500** points and lasts until Monday!\n'
            'Please select the horses to register.',
            ephemeral=True,
            view=horse_view
        )
        await horse_view.wait()
        selected = horse_view.horses_selected.copy()
        if len(selected) < 1:
            await interaction.edit_original_response(content='View Timed Out',
                                                     view=None)
            return
        points_to_take = 500 * len(selected)
        if member.points < points_to_take:
            await interaction.edit_original_response(
                content=f'You selected **{len(selected)}** horses which costs '
                        f'**{points_to_take:,}** and you only have '
                        f'**{member.points:,}**!',
                view=None
            )
            return
        member.points -= points_to_take
        await member.save()
        for horse in selected:
            horse.set_flag('REGISTERED', True)
            await horse.save()
        await interaction.edit_original_response(
            content=f'Successfully registered '
                    f'**{", ".join(x.name for x in selected)}** for '
                    f'**{points_to_take:,}** points!',
            view=None
        )
