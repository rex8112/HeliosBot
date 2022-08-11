from typing import Optional, TYPE_CHECKING

import discord

from .types import HeliosChannel

if TYPE_CHECKING:
    from .helios_bot import HeliosBot


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
