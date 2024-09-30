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
from typing import TYPE_CHECKING

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from helios import DynamicVoiceGroup, VoiceManager, PaginatorSelectView

if TYPE_CHECKING:
    from helios import HeliosBot

logger = logging.getLogger('Helios.DynamicVoiceCog')


class DynamicVoiceCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    async def cog_unload(self) -> None:
        ...

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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        server = self.bot.servers.get(member.guild.id)
        server.channels.dynamic_voice.pug_manager.on_member_join(member)


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
