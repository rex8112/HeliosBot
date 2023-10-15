import datetime
import math
import re
from types import MethodType
from typing import Optional, TYPE_CHECKING, Type, Any

import peewee
from discord import Interaction
from typing_extensions import Self

import discord

from .database import objects, ViolationModel
from .modals import VoiceNameChange
from .types import HeliosChannel

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .channel import VoiceChannel
    from .server import Server
    from .member import HeliosMember
    from .violation import Violation


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


class VoiceControllerView(discord.ui.View):
    def __init__(self, server: 'Server', channel: discord.VoiceChannel, *,
                 name: str = 'Unnamed', maximum: int = 10, allow_dead=False):
        super().__init__(timeout=None)
        self.server = server
        self.server.voice_controllers.append(self)
        self.channel = channel
        self.message: Optional[discord.Message] = None
        self.voice_role = server.voice_controller_role
        self.synced = channel.permissions_synced
        self.name = name
        self.max = maximum
        self.running = False
        self.mute = False
        self.deafen = False
        self.members: list[discord.Member] = []
        if not allow_dead:
            self.remove_item(self.die_button)

    @property
    def host(self) -> Optional[discord.Member]:
        if len(self.members) > 0:
            return self.members[0]
        return None

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title=self.name
        )
        mem_string = ''
        for mem in self.members:
            if mem == self.host:
                mem_string += f'{mem.display_name} - HOST\n'
            else:
                mem_string += f'{mem.display_name}\n'
        embed.add_field(name='Members', value=mem_string)
        embed.set_footer(text=f'{len(self.members)}/{self.max}')
        return embed

    async def join(self, mem: discord.Member):
        if mem not in self.members:
            if mem.voice:
                self.members.append(mem)
                await mem.add_roles(self.voice_role,
                                    reason='Joined Voice Controller')
                if self.running:
                    await self.activate(mem)
                return True
        return False

    async def leave(self, mem: discord.Member):
        if mem in self.members:
            self.members.remove(mem)
            if mem.voice:
                await mem.remove_roles(self.voice_role,
                                       reason='Left Voice Controller')
                if self.running:
                    await self.deactivate(mem)
            return True
        return False

    def is_activated(self, member: discord.Member):
        if not member.voice:
            return False
        if self.mute:
            return member.voice.mute
        if self.deafen:
            return member.voice.deaf

    async def activate(self, member: discord.Member):
        apply = {}
        if self.mute:
            apply['mute'] = True
        if self.deafen:
            apply['deafen'] = True
        try:
            await member.edit(**apply)
        except (discord.Forbidden, discord.HTTPException):
            ...

    async def deactivate(self, member: discord.Member):
        apply = {}
        if self.mute:
            apply['mute'] = False
        if self.deafen:
            apply['deafen'] = False
        try:
            await member.edit(**apply)
        except (discord.Forbidden, discord.HTTPException):
            ...

    @discord.ui.button(label='Start', style=discord.ButtonStyle.green, row=0)
    async def start_button(self, interaction: discord.Interaction,
                           button: discord.Button):
        if interaction.user == self.host:
            await interaction.response.defer()
            for mem in self.members:
                await self.activate(mem)
            self.running = True
            self.start_button.disabled = True
            self.stop_button.disabled = False
            await interaction.edit_original_response(embed=self.embed, view=self)

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.gray, row=0,
                       disabled=True)
    async def stop_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user == self.host:
            await interaction.response.defer()
            for mem in self.members:
                await self.deactivate(mem)
            self.running = True
            self.start_button.disabled = False
            self.stop_button.disabled = True
            await interaction.edit_original_response(embed=self.embed, view=self)

    @discord.ui.button(label='Died', style=discord.ButtonStyle.gray, row=0)
    async def die_button(self, interaction: discord.Interaction,
                         button: discord.Button):
        mem = interaction.user
        if mem not in self.members:
            await interaction.response.send_message(
                'You are not in this controller', ephemeral=True)
            return
        if self.running:
            if self.is_activated(mem):
                await self.deactivate(mem)
                await interaction.response.send_message('You died!',
                                                        ephemeral=True)
            else:
                await self.activate(mem)
                await interaction.response.send_message(
                    'You have come back from the dead!', ephemeral=True)
        else:
            await interaction.response.send_message(
                'The controller is not currently running.', ephemeral=True
            )

    @discord.ui.button(label='Close', style=discord.ButtonStyle.red, row=0)
    async def close_button(self, interaction: discord.Interaction,
                           button: discord.Button):
        if interaction.user == self.host:
            for mem in self.members:
                if self.is_activated(mem):
                    await self.deactivate(mem)
                    await mem.remove_roles(self.voice_role)
            self.running = False
            self.server.voice_controllers.remove(self)
            self.stop()
            await interaction.response.edit_message(embed=self.embed,
                                                    view=None)

    @discord.ui.button(label='Join', style=discord.ButtonStyle.blurple, row=1)
    async def join_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if self.message is None:
            self.message = interaction.message
        if len(self.members) < self.max:
            await self.join(interaction.user)
            await interaction.response.edit_message(embed=self.embed)
        else:
            await interaction.response.send_message(
                'Controller is at max capacity.',
                ephemeral=True
            )

    @discord.ui.button(label='Leave', style=discord.ButtonStyle.gray, row=1)
    async def leave_button(self, interaction: discord.Interaction,
                           button: discord.Button):
        if len(self.members) > 1:
            await self.leave(interaction.user)
            await interaction.response.send_message('Left!', ephemeral=True)
            await self.message.edit(embed=self.embed)
        else:
            await interaction.response.send_message('You are the last member, hit close instead.', ephemeral=True)

    @discord.ui.button(label='Kick', style=discord.ButtonStyle.red, row=1)
    async def kick_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user == self.host and len(self.members) > 1:
            kick_view = Selector(self.members, max_value=len(self.members) - 1)
            await interaction.response.send_message('Choose who to kick',
                                                    view=kick_view,
                                                    ephemeral=True)
            await kick_view.wait()
            if kick_view.values:
                for mem in kick_view.values:
                    if len(self.members) > 1:
                        await self.leave(mem)

                await self.message.edit(embed=self.embed)


class Selector(discord.ui.View):
    def __init__(self, options: list, *, min_value=1, max_value=1,
                 author=None, timeout=15):
        super().__init__(timeout=timeout)
        self.names = None
        self.values = None
        self.author = author
        self.options = {}
        for o in options:
            self.options[str(o)] = o
        self.select_options = [
            discord.SelectOption(label=x) for x in self.options.keys()
        ]
        self.selections_picked.max_values = max_value
        self.selections_picked.min_values = min_value
        self.selections_picked.options = self.select_options

    @discord.ui.select()
    async def selections_picked(self, interaction: discord.Interaction,
                                select: discord.ui.Select):
        allowed = True
        if self.author:
            if self.author != interaction.user:
                allowed = False

        if allowed:
            await interaction.response.defer()
            self.values = []
            for v in select.values:
                self.values.append(self.options[v])
            self.stop()


class YesNoView(discord.ui.View):
    def __init__(self, author: discord.Member, *, timeout=5):
        super().__init__(timeout=timeout)
        self.author = author
        self.value = None


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
            return
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
        await interaction.response.defer()
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
        await interaction.response.defer()
        await voice.update_permissions(template)
        await voice.update_message()
        await template.save()


class VerifyView(discord.ui.View):
    def __init__(self, member: 'HeliosMember'):
        super().__init__(timeout=None)
        self.member = member
        self.server = member.server

    @discord.ui.button(label='Verify', style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button: discord.Button):
        requester = self.server.members.get(interaction.user.id)
        if requester and requester.verified:
            await self.member.verify()
            embed = discord.Embed(
                title='Verified!',
                description=f'{self.member.member} is now Verified!',
                colour=discord.Colour.green()
            )
            embed.set_author(name=str(requester.member),
                             icon_url=requester.member.avatar.url)
            button.label = 'Verified'
            button.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
            return
        embed = discord.Embed(
            title='You are not Verified!',
            description='Please get a friend who is verified to hit this button.',
            colour=discord.Colour.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


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


class ShopView(discord.ui.View):
    def __init__(self, server: 'Server'):
        super().__init__(timeout=None)
        self.bot = server.bot
        self.shop = server.shop
        self.server = server
        self.make_buttons()

    def make_buttons(self):
        for item in self.shop.items:
            async def callback(s: discord.ui.Button, interaction: discord.Interaction):
                author = self.server.members.get(interaction.user.id)
                await item.purchase(author, interaction)
            button = discord.ui.Button(
                style=discord.ButtonStyle.grey,
                label=item.name,
                custom_id=f'helios:{self.server.id}:shop:{item.name.lower().replace(" ", "")}'
            )
            button.callback = MethodType(callback, button)
            self.add_item(button)


class TempMuteView(discord.ui.View):
    PRICE_PER_SECOND = 1

    def __init__(self, author: 'HeliosMember'):
        super().__init__(timeout=60)
        self.author = author
        self.selected_member: Optional['HeliosMember'] = None
        self.selected_seconds: int = 5
        self.value = 0
        self.confirmed = False
        self.error_message: str = ''

    async def get_value(self):
        if not self.selected_member:
            return 0
        minutes = await self.selected_member.get_point_mutes()
        return int((self.selected_seconds * self.PRICE_PER_SECOND) * math.pow(2, minutes))

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title='Temp Mute',
            colour=discord.Colour.blurple(),
            description=self.error_message
        )
        embed.add_field(name='Target',
                        value=f'{self.selected_member.member.display_name if self.selected_member else "None"}')
        embed.add_field(name='Duration', value=f'{self.selected_seconds} Seconds')
        embed.add_field(name='Price', value=f'{self.value} {self.author.server.points_name.capitalize()}')
        embed.set_footer(text=f'Your {self.author.server.points_name.capitalize()}: {self.author.points}')
        if self.selected_member:
            embed.set_thumbnail(url=self.selected_member.member.display_avatar.url)
        return embed

    async def reload_message(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.value = await self.get_value()
        embed = self.get_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    async def verify_member(self, member: discord.Member):
        member: 'HeliosMember' = self.author.server.members.get(member.id)
        if member.is_noob():
            self.error_message = f'{member.member.display_name} is still too new to be muted.'
            self.selected_member = None
            return False
        if not member.member.voice:
            self.error_message = f'{member.member.display_name} is not in a voice channel.'
            self.selected_member = None
            return False
        if member.member.voice.mute:
            self.error_message = f'{member.member.display_name} is already muted.'
            self.selected_member = None
            return False
        # if member.member.top_role > member.member.guild.me.top_role or member.member.guild.owner == member.member:
        #     self.error_message = f'I am sorry, I could not mute {member.member.display_name} even if I wanted to.'
        #     self.selected_member = None
        #     return False
        return True

    @discord.ui.select(cls=discord.ui.UserSelect, row=0)
    async def member_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        member: discord.Member = select.values[0]
        if not await self.verify_member(member):
            await self.reload_message(interaction)
            return
        member: 'HeliosMember' = self.author.server.members.get(member.id)
        self.selected_member = member
        self.error_message = ''
        await self.reload_message(interaction)

    @discord.ui.button(label='5s', style=discord.ButtonStyle.grey, row=1)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 5
        await self.reload_message(interaction)

    @discord.ui.button(label='15s', style=discord.ButtonStyle.grey, row=1)
    async def second_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 15
        await self.reload_message(interaction)

    @discord.ui.button(label='30s', style=discord.ButtonStyle.grey, row=1)
    async def third_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 30
        await self.reload_message(interaction)

    @discord.ui.button(label='45s', style=discord.ButtonStyle.grey, row=1)
    async def fourth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 45
        await self.reload_message(interaction)

    @discord.ui.button(label='60s', style=discord.ButtonStyle.grey, row=1)
    async def fifth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        self.selected_seconds = 60
        await self.reload_message(interaction)

    @discord.ui.button(label='Purchase', style=discord.ButtonStyle.green, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        if not await self.verify_member(self.selected_member.member):
            await self.reload_message(interaction)
            return
        await interaction.response.defer()
        self.confirmed = True
        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author.member:
            await interaction.response.send_message(content='You are not allowed to use this.', ephemeral=True)
            return
        await interaction.response.defer()
        self.stop()


