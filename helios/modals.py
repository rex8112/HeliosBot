import traceback
from typing import TYPE_CHECKING

from discord import ui, Interaction

from .exceptions import BetError
from .horses.enumerations import BetType

if TYPE_CHECKING:
    from .server import Server
    from .member import HeliosMember
    from .horses.race import EventRace
    from .helios_bot import HeliosBot


class TopicCreation(ui.Modal, title='New Topic'):
    name = ui.TextInput(label='Name')

    async def on_submit(self, interaction: Interaction) -> None:
        bot: 'HeliosBot' = interaction.client
        server: 'Server' = bot.servers.get(interaction.guild_id)
        result, result_message = await server.channels.create_topic(self.name.value, interaction.user)
        await interaction.response.send_message(result_message, ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        traceback.print_exc()
        await interaction.response.send_message('Sorry, something went wrong.', ephemeral=True)


class BetModal(ui.Modal, title=f'Bet'):
    type = ui.TextInput(label='Bet Type', placeholder='win, place, show', required=True)
    horse_name = ui.TextInput(label='Horse', placeholder='HorsesName', required=True)
    amount = ui.TextInput(label='Amount', required=True)

    def __init__(self, er: 'EventRace', member: 'HeliosMember'):
        super().__init__(title=f'{er.name} Bet', timeout=er.time_until_race.seconds)
        self.race = er
        self.member = member

    async def on_submit(self, interaction: Interaction) -> None:
        types: dict[str, BetType] = {
            'win': BetType.win,
            'place': BetType.place,
            'show': BetType.show
        }
        if self.type.value.lower() not in ['place', 'win', 'show']:
            raise BetError('Type must be win, place, or show.')
        try:
            amt = int(self.amount.value)
        except ValueError:
            raise BetError('Must input a valid number.')
        horse = self.race.find_horse(self.horse_name.value)
        if horse is None:
            raise BetError('You must type a valid horse name that is registered to this race.')
        if self.member.points < amt:
            raise BetError(f'You only have {self.member.points} points')
        self.race.bet(types[self.type.value.lower()], self.member, horse, amt)
        self.member.points -= amt
        await self.member.save()
        await self.race.save()
        await interaction.response.send_message(
            f'You have placed a {types[self.type.value.lower()].name} bet on {horse.name} for {amt}.', ephemeral=True)
        await self.race.message.edit(embed=self.race.get_betting_embed())

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        if isinstance(error, BetError):
            await interaction.response.send_message(str(error), ephemeral=True)
        else:
            traceback.print_exc()
            await interaction.response.send_message('Sorry, something went wrong.', ephemeral=True)
