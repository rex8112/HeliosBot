from typing import Optional, TYPE_CHECKING

import discord

from .types import HeliosChannel

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .server import Server


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
            mem_string += f'{mem.display_name}\n'
        embed.add_field(name='Members', value=mem_string)
        return embed

    async def join(self, mem: discord.Member):
        if mem not in self.members:
            if mem.voice:
                self.members += mem
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
        if self.voice_role not in member.roles:
            return
        apply = {}
        if self.mute:
            apply['mute'] = True
        if self.deafen:
            apply['deafen'] = True
        await member.edit(**apply)

    async def deactivate(self, member: discord.Member):
        if self.voice_role not in member.roles:
            return
        apply = {}
        if self.mute:
            apply['mute'] = False
        if self.deafen:
            apply['deafen'] = False
        await member.edit(**apply)

    @discord.ui.button(label='Start', style=discord.ButtonStyle.green, row=0)
    async def start_button(self, interaction: discord.Interaction,
                           button: discord.Button):
        if interaction.user == self.host:
            for mem in self.members:
                await self.activate(mem)
            self.running = True
            self.start_button.disabled = True
            self.stop_button.disabled = False
            await interaction.response.edit_message(embed=self.embed)

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.gray, row=0,
                       disabled=True)
    async def stop_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user == self.host:
            for mem in self.members:
                await self.deactivate(mem)
            self.running = True
            self.start_button.disabled = False
            self.stop_button.disabled = True
            await interaction.response.edit_message(embed=self.embed)

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
        await self.leave(interaction.user)
        await interaction.response.send_message('Left!', ephemeral=True)

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
        self.select = discord.ui.Select(
            min_values=min_value,
            max_values=max_value,
            options=self.select_options
        )
        self.add_item(self.select)

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
