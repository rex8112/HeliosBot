import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from helios import HeliosBot


logger = logging.getLogger('Helios.PrivateVoiceCog')


class PrivateVoiceCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.context_menu(name='Allow in Voice')
    async def allow(self, interaction: discord.Interaction, member: discord.Member):
        server = self.bot.servers.get(interaction.user.id)
        if server:
            private_voices = server.channels.get_type('private_voice')
            owned = list(filter(lambda x: x.owner == interaction.user, private_voices))
            await interaction.response.defer(ephemeral=True)
            if len(owned) > 0:
                channel = owned[0]
                await channel.allow(member)
                await interaction.followup.send(f'{member.mention} Allowed in {channel.channel.mention}.')
            else:
                await interaction.followup.send(f'You do not currently have a channel active.')
        else:
            await interaction.response.send_message(
                'Critical Failure, tell `rex8112#1200` that server initialization failed.'
            )

    @app_commands.context_menu(name='Deny in Voice')
    async def deny(self, interaction: discord.Interaction, member: discord.Member):
        server = self.bot.servers.get(interaction.user.id)
        if server:
            private_voices = server.channels.get_type('private_voice')
            owned = list(filter(lambda x: x.owner == interaction.user, private_voices))
            await interaction.response.defer(ephemeral=True)
            if len(owned) > 0:
                channel = owned[0]
                await channel.deny(member)
                await interaction.followup.send(f'{member.mention} Denied in {channel.channel.mention}.')
            else:
                await interaction.followup.send(f'You do not currently have a channel active.')
        else:
            await interaction.response.send_message(
                'Critical Failure, tell `rex8112#1200` that server initialization failed.'
            )


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(PrivateVoiceCog(bot))
