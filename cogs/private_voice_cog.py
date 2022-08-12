import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from helios import HeliosBot, VoiceTemplate


logger = logging.getLogger('Helios.PrivateVoiceCog')


class PrivateVoiceCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.allow_context = app_commands.ContextMenu(
            name='Allow in Voice',
            callback=self.allow,
        )
        self.deny_context = app_commands.ContextMenu(
            name='Deny in Voice',
            callback=self.deny
        )
        self.bot.tree.add_command(self.allow_context)
        self.bot.tree.add_command(self.deny_context)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        if not after:
            return
        server = self.bot.servers.get(member.guild.id)
        mem = server.members.get(member.id)
        create_channel = server.private_create_channel
        if after.channel == create_channel:
            if len(mem.templates) > 0:
                last_template = mem.templates[-1]
            else:
                last_template = VoiceTemplate(mem, mem.member.name)
                mem.templates.append(last_template)
                await mem.save()
            server.channels.create_private_voice(mem, last_template)

    async def allow(self, interaction: discord.Interaction, user: discord.Member):
        server = self.bot.servers.get(interaction.guild_id)
        if server:
            private_voices = server.channels.get_type('private_voice')
            owned = list(filter(lambda x: x.owner == interaction.user, private_voices))
            await interaction.response.defer(ephemeral=True)
            if len(owned) > 0:
                channel = owned[0]
                await channel.allow(user)
                await interaction.followup.send(f'{user.mention} Allowed in {channel.channel.mention}.')
            else:
                await interaction.followup.send(f'You do not currently have a channel active.')
        else:
            await interaction.response.send_message(
                'Critical Failure, tell `rex8112#1200` that server initialization failed.'
            )

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
