import re
from typing import TYPE_CHECKING

import discord
import peewee
from typing_extensions import Self

if TYPE_CHECKING:
    from ..violation import Violation
    from ..helios_bot import HeliosBot
    from ..server import Server

__all__ = ('ViolationView', 'ViolationPayButton')


class ViolationPayButton(discord.ui.DynamicItem[discord.ui.Button],
                         template=r'helios:(?P<server>[0-9]+):violation:(?P<id>[0-9]+)'):
    def __init__(self, server_id: int, violation_id: int):
        super().__init__(
            discord.ui.Button(
                label='Pay',
                style=discord.ButtonStyle.green,
                custom_id=f'helios:{server_id}:violation:{violation_id}'
            )
        )
        self.server_id = server_id
        self.violation_id = violation_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Item, match: re.Match[str], /) -> Self:
        return cls(int(match['server']), int(match['id']))

    async def callback(self, interaction: discord.Interaction):
        try:
            bot: 'HeliosBot' = interaction.client
            server = bot.servers.get(self.server_id)
            violation: 'Violation' = await server.court.get_violation(self.violation_id)

            if violation.paid:
                await interaction.response.send_message(content='You have already paid this fine.', ephemeral=True)
                return

            if await violation.pay():
                await interaction.response.send_message(content='Paid!', ephemeral=True)
            else:
                await interaction.response.send_message(content=f'Not enough {server.points_name.capitalize()}', ephemeral=True)
        except peewee.DoesNotExist:
            await interaction.response.send_message(content='This violation does not exist', ephemeral=True)


class ViolationView(discord.ui.View):
    def __init__(self, server: 'Server', violation_id):
        super().__init__()
        self.bot = server.bot
        self.server = server
        self.add_item(ViolationPayButton(server.id, violation_id))
