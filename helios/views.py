from typing import Optional, TYPE_CHECKING

import discord

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
        else:
            self.bet.disabled = True

    @discord.ui.button(label='Bet', style=discord.ButtonStyle.blurple, disabled=True)
    async def bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self.race.stadium.server.members.get(interaction.user.id)
        await interaction.response.send_modal(BetModal(self.race, member))  # Modal handles all further actions

    @discord.ui.button(label='Register', style=discord.ButtonStyle.gray, disabled=True)
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show register view, wait for its completion, fill values
        member = self.race.stadium.server.members.get(interaction.user.id)
        horses = list(filter(lambda x: self.race.is_qualified(x), member.horses.values()))
        horse_strings = []
        for i, h in enumerate(horses):
            horse_strings.append(f'{i}. {h.name}')
        # TODO: Call register view
