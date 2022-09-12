import datetime
import traceback
from typing import TYPE_CHECKING

from discord import ui, Interaction

if TYPE_CHECKING:
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
