import datetime
import re
import traceback
from typing import TYPE_CHECKING

from discord import ui, Interaction

if TYPE_CHECKING:
    from .horse import Horse
    from .auction import HorseListing
    from ..member import HeliosMember


class SetBidModal(ui.Modal):
    amount = ui.TextInput(label='Amount', placeholder='Amount to bid',
                          required=True)

    def __init__(self, listing: 'HorseListing', member: 'HeliosMember'):
        remaining = listing.end_time - datetime.datetime.now().astimezone()
        super().__init__(title=f'{listing.horse.name} Auction',
                         timeout=remaining.total_seconds())
        self.listing = listing
        self.member = member

    async def on_submit(self, interaction: Interaction) -> None:
        amount = int(self.amount.value)
        if len(self.listing.bids) > 0:
            cur_bid = self.listing.get_highest_bidder().amount + 1
        else:
            cur_bid = self.listing.settings['min_bid']
        if amount > self.member.points:
            await interaction.response.send_message(
                f'You only have **{self.member.points:,}** points!',
                ephemeral=True
            )
            return
        elif not self.listing.can_bid(self.member, amount):
            await interaction.response.send_message(
                f'You have achieved the maximum allowed horses.',
                ephemeral=True
            )
            return
        if amount < cur_bid:
            await interaction.response.send_message(
                f'You must bid at least **{cur_bid:,}** points.',
                ephemeral=True
            )
            return
        self.listing.bid(self.member, amount)
        await interaction.response.send_message(
            f'You have bid **{amount:,}** points!',
            ephemeral=True
        )

    async def on_error(self, interaction: Interaction,
                       error: Exception) -> None:
        traceback.print_exc()
        await interaction.response.send_message(
            'Sorry, something unexpected went wrong.', ephemeral=True
        )


class NameChangeModal(ui.Modal):
    name = ui.TextInput(label='New Name', max_length=26, min_length=3)

    def __init__(self, horse: 'Horse'):
        self.horse = horse
        super().__init__(title=f'Horse Name Change', timeout=30)

    async def on_submit(self, interaction: Interaction) -> None:
        matches = re.search(r"^[\w\- ']+$", self.name.value)
        if matches is None:
            await interaction.response.send_message('Please use alphanumeric '
                                                    'characters')
            return
        name = matches[0]
        if len(name) < 3:
            await interaction.response.send_message('Name must be longer than '
                                                    '3 characters')
            return
        horse = self.horse.stadium.get_horse_name(name)
        if horse:
            await interaction.response.send_message('Name is already taken.',
                                                    ephemeral=True)
            return
        self.horse.name = name
        await interaction.response.defer(ephemeral=True)
        await self.horse.save()
        await interaction.edit_original_response(
            content='Name changed successfully!',
            embeds=self.horse.get_inspect_embeds(is_owner=True)
        )
