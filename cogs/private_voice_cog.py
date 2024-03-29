import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from helios import VoiceTemplate

if TYPE_CHECKING:
    from helios import HeliosBot, VoiceChannel


logger = logging.getLogger('Helios.PrivateVoiceCog')


class PrivateVoiceCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.allow_context = app_commands.ContextMenu(
            name="Allow in Voice",
            callback=self.allow
        )
        self.deny_context = app_commands.ContextMenu(
            name="Deny in Voice",
            callback=self.deny
        )
        self.clear_context = app_commands.ContextMenu(
            name="Clear from Voice",
            callback=self.clear
        )

        self.bot.tree.add_command(self.allow_context)
        self.bot.tree.add_command(self.deny_context)
        self.bot.tree.add_command(self.clear_context)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.allow_context.name, type=self.allow_context.type)
        self.bot.tree.remove_command(self.deny_context.name, type=self.deny_context.type)
        self.bot.tree.remove_command(self.clear_context.name, type=self.clear_context.type)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        if not after:
            return
        await self.bot.wait_until_ready()
        server = self.bot.servers.get(member.guild.id)
        mem = server.members.get(member.id)
        create_channel = server.private_create_channel
        if after.channel == create_channel and create_channel is not None:
            voices = [x for x in server.channels.get_type('private_voice')
                      if x.owner == mem]
            if len(voices) > 0:
                voice: 'VoiceChannel' = voices[0]
                await mem.member.move_to(voice.channel,
                                         reason='Private channel already '
                                                'exists')
                return
            if len(mem.templates) > 0:
                last_template = mem.templates[-1]
            else:
                last_template = VoiceTemplate(mem, mem.member.name)
                mem.templates.append(last_template)
                await mem.save(force=True)
            voice = await server.channels.create_private_voice(
                mem,
                template=last_template
            )
            await voice.save()
            await mem.member.move_to(voice.channel,
                                     reason='Created private Voice Channel.')

    async def allow(self, interaction: discord.Interaction,
                    user: discord.Member):
        server = self.bot.servers.get(interaction.guild_id)
        if server:
            private_voices = server.channels.get_type('private_voice')
            owned = list(filter(lambda x: x.owner == interaction.user,
                                private_voices))
            await interaction.response.defer(ephemeral=True)
            if len(owned) > 0:
                channel = owned[0]
                await channel.allow(user)
                await interaction.followup.send(f'{user.mention} Allowed in '
                                                f'{channel.channel.mention}.')
            else:
                await interaction.followup.send(f'You do not currently have a '
                                                f'channel active.')
        else:
            await interaction.response.send_message(
                'Critical Failure, tell `rex8112#1200` that server '
                'initialization failed.'
            )

    async def deny(self, interaction: discord.Interaction,
                   member: discord.Member):
        server = self.bot.servers.get(interaction.guild_id)
        if server:
            private_voices = server.channels.get_type('private_voice')
            owned = list(filter(lambda x: x.owner == interaction.user,
                                private_voices))
            await interaction.response.defer(ephemeral=True)
            if len(owned) > 0:
                channel = owned[0]
                await channel.deny(member)
                await interaction.followup.send(f'{member.mention} Denied '
                                                f'in {channel.channel.mention}'
                                                '.')
            else:
                await interaction.followup.send(f'You do not currently have a '
                                                f'channel active.')
        else:
            await interaction.response.send_message(
                'Critical Failure, tell `rex8112#1200` that server '
                'initialization failed.'
            )

    async def clear(self, interaction: discord.Interaction,
                    member: discord.Member):
        server = self.bot.servers.get(interaction.guild_id)
        if server:
            private_voices = server.channels.get_type('private_voice')
            owned = list(filter(lambda x: x.owner == interaction.user,
                                private_voices))
            await interaction.response.defer(ephemeral=True)
            if len(owned) > 0:
                channel = owned[0]
                await channel.clear(member)
                await interaction.followup.send(f'{member.mention} Cleared '
                                                f'from {channel.channel.mention}'
                                                '.')
            else:
                await interaction.followup.send(f'You do not currently have a '
                                                f'channel active.')
        else:
            await interaction.response.send_message(
                'Critical Failure, tell `rex8112#1200` that server '
                'initialization failed.'
            )


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(PrivateVoiceCog(bot))
