import datetime
from typing import Optional, TYPE_CHECKING

import discord

from .modals import VoiceNameChange
from .types import HeliosChannel

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .channel import VoiceChannel


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


class VoiceView(discord.ui.View):
    def __init__(self, voice: 'VoiceChannel'):
        super().__init__(timeout=None)
        self.bot = voice.bot
        self.voice = voice
        if self.voice.get_template().private:
            self.whitelist.disabled = True
        else:
            self.blacklist.disabled = True

    def get_channel(self, guild_id: int,
                    channel_id: int) -> Optional['HeliosChannel']:
        server = self.bot.servers.get(guild_id)
        if server:
            channel = server.channels.get(channel_id)
            return channel
        return None

    @discord.ui.button(label='Change Name', style=discord.ButtonStyle.gray,
                       custom_id='voice:name')
    async def change_name(self, interaction: discord.Interaction,
                          _: discord.ui.Button):
        voice: 'VoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
        now = datetime.datetime.now().astimezone()
        if voice.next_name_change() <= now:
            await interaction.response.send_modal(VoiceNameChange(voice))
        else:
            await interaction.response.send_message(
                f'Try again <t:{int(voice.next_name_change().timestamp())}:R>',
                ephemeral=True
            )

    @discord.ui.button(label='Make Private', style=discord.ButtonStyle.green)
    async def whitelist(self, interaction: discord.Interaction,
                        _: discord.ui.Button):
        voice: 'VoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
        template = voice.get_template()
        template.private = True
        await voice.update_permissions(template)
        await voice.update_message()
        await template.save()

    @discord.ui.button(label='Make Public', style=discord.ButtonStyle.red)
    async def blacklist(self, interaction: discord.Interaction,
                        _: discord.ui.Button):
        voice: 'VoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
        template = voice.get_template()
        template.private = False
        await voice.update_permissions(template)
        await voice.update_message()
        await template.save()
