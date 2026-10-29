#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import logging
import traceback
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from helios import DynamicVoiceGroup, VoiceManager, PaginatorSelectView, Colour

if TYPE_CHECKING:
    from helios import HeliosBot

logger = logging.getLogger('Helios.DynamicVoiceCog')


async def send_bad_afk_message(member: discord.Member, target: discord.Member):
    img = discord.File('./helios/resources/help/AFKAppMenu.png', filename='afk.png')
    embed = discord.Embed(title='Improper AFK',
                          description=f'You AFKed {target.name} using moderator abilities. Please use the bot '
                                      f'commands by right clicking them.',
                          colour=Colour.error())
    embed.set_image(url='attachment://afk.png')
    await member.send(file=img, embed=embed)


class DynamicVoiceCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

        self.afk_context = app_commands.ContextMenu(
            name='AFK Check',
            callback=self.afk_check,
        )
        self.bot.tree.add_command(self.afk_context)

    async def cog_unload(self) -> None:
        ...

    async def afk_check(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(message='You must be in a voice channel to use this feature.', ephemeral=True)
        if not member.voice or not member.voice.channel:
            return await interaction.response.send_message(message='This person is not in a voice channel.', ephemeral=True)
        if member.voice and member.voice.channel is member.guild.afk_channel:
            return await interaction.response.send_message(message='This person is already in the AFK Channel.', ephemeral=True)

        server = self.bot.servers.get(interaction.guild_id)
        h_afker = server.members.get(interaction.user.id)
        h_mem = server.members.get(member.id)
        if server.cooldowns.on_cooldown('afk_check', h_mem):
            return await interaction.response.send_message('This person has already been AFK checked recently.', ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        if await h_mem.afk_check(h_afker):
            server.cooldowns.set_duration('afk_check', h_mem, 1 * 60 * 60)
            return await interaction.followup.send(f'{h_mem} successfully AFKed.')
        else:
            return await interaction.followup.send(f'{h_mem} not AFKed.')

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState
                                    ):
        if before.channel is None or after.channel is None:
            return
        server = self.bot.servers.get(member.guild.id)
        h_mem = server.members.get(member.id)
        if after.channel is member.guild.afk_channel:
            if h_mem.afk_information:
                return
            if not await h_mem.was_afk_checked(): # Check if h_mem was put into the AFK channel with moderator powers.
                return
            await send_bad_afk_message(h_mem.afk_information[0].member, member)
        elif before.channel is member.guild.afk_channel:
            ago = discord.utils.utcnow() - timedelta(seconds=60)
            afker = h_mem.afk_information[0]
            if not h_mem.afk_information:
                return
            if h_mem.afk_information[1] > ago and afker.member.voice and afker.member.voice.channel:
                await afker.temp_mute(60, h_mem, 0, bad_afk=True)
            h_mem.afk_information = None

    @app_commands.command(name='groups', description='Manage all dynamic voice groups.')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def groups(self, interaction: discord.Interaction):
        """Manage all dynamic voice groups."""
        server = self.bot.servers.get(interaction.guild_id)
        if server.settings.dynamic_voice_category.value is None:
            await interaction.response.send_message('Dynamic voice channels are not enabled on this server.',
                                                    ephemeral=True)
            return
        vm: VoiceManager = server.channels.dynamic_voice
        view = DynamicVoiceView(interaction.user, vm)
        await interaction.response.send_message('Select an option.', view=view, ephemeral=True)


# noinspection PyUnresolvedReferences
class DynamicVoiceView(discord.ui.View):
    def __init__(self, author: discord.Member, vm: VoiceManager):
        super().__init__()
        self.author = author
        self.vm = vm

    async def on_timeout(self) -> None:
        ...

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        return interaction.user.id == self.author.id

    @discord.ui.button(label='Create Group', style=discord.ButtonStyle.primary)
    async def create_group(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = NewGroupModal(self.vm)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Delete Group', style=discord.ButtonStyle.danger)
    async def delete_group(self, interaction: discord.Interaction, button: discord.ui.Button):
        def get_embeds(groups: list[DynamicVoiceGroup]) -> list[discord.Embed]:
            embed = discord.Embed(title='Delete Group', color=discord.Color.red())
            embed.description = 'Select a group to delete. THERE IS NO CONFIRMATION BECAUSE I AM LAZY.'
            [embed.add_field(name=f'{group.name} ({group.id})',
                             value=f'{len(group.channels)} channels') for group in groups]
            return [embed]

        names = [f'{group.name} ({group.id})' for group in self.vm.groups.values()]
        view: 'PaginatorSelectView[DynamicVoiceGroup]' = PaginatorSelectView(list(self.vm.groups.values()),
                                                                             names, get_embeds)

        await interaction.response.send_message('Select a group to delete.', view=view, ephemeral=True)

        if await view.wait():
            return

        group = view.selected
        if group is None:
            return

        await interaction.edit_original_response(content='Group deleted.', view=None)
        await self.vm.delete_group(group)


class NewGroupModal(discord.ui.Modal, title='New Group'):
    minimum = discord.ui.TextInput(label='Minimum', min_length=1, max_length=2)
    maximum = discord.ui.TextInput(label='Maximum', min_length=1, max_length=2)
    minimum_empty = discord.ui.TextInput(label='Minimum Empty', min_length=1, max_length=2)
    template = discord.ui.TextInput(label='Template', placeholder='Use {n} for channel number.', min_length=3,
                                    max_length=25)
    game_template = discord.ui.TextInput(label='Game Template', placeholder='Use {n} for channel number and {g} for '
                                                                            'game name.', min_length=3, max_length=22)

    def __init__(self, vm: VoiceManager):
        super().__init__()
        self.vm = vm

    async def on_submit(self, interaction: discord.Interaction) -> None:
        error = self.validate_input()
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        await interaction.response.send_message('Creating group...', ephemeral=True)
        await self.vm.create_group(int(self.minimum.value), int(self.minimum_empty.value),
                                   self.template.value, self.game_template.value, int(self.maximum.value))

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        traceback.print_exc()
        await interaction.response.send_message('Sorry, something went wrong.', ephemeral=True)

    def validate_input(self) -> str:
        try:
            int(self.minimum.value)
            int(self.maximum.value)
            int(self.minimum_empty.value)
        except ValueError:
            return 'minimum, maximum, and minimum_empty must be integers.'

        if int(self.minimum.value) > int(self.maximum.value):
            return 'minimum must be less than or equal to maximum.'
        if int(self.minimum_empty.value) > int(self.maximum.value):
            return 'minimum_empty must be less than or equal to maximum.'
        return ''


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(DynamicVoiceCog(bot))
