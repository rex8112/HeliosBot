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

from typing import Optional, TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ..server import Server

__all__ = ('VoiceControllerView',)


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
        self.deafen = True
        self.members: list[discord.Member] = []
        if not allow_dead:
            self.remove_item(self.die_button)

        self.mute_button.style = discord.ButtonStyle.green if self.mute else discord.ButtonStyle.red
        self.deafen_button.style = discord.ButtonStyle.green if self.deafen else discord.ButtonStyle.red

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
        try:
            member = self.server.members.get(member.id)
            if self.mute and self.deafen:
                await member.voice_mute_deafen(reason='Voice Controller')
            if self.mute:
                await member.voice_mute(reason='Voice Controller')
            if self.deafen:
                await member.voice_deafen(reason='Voice Controller')
        except (discord.Forbidden, discord.HTTPException):
            ...

    async def deactivate(self, member: discord.Member):
        try:
            member = self.server.members.get(member.id)
            await member.voice_unmute_undeafen(reason='Voice Controller')
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
            self.mute_button.disabled = True
            self.deafen_button.disabled = True
            await interaction.edit_original_response(embed=self.embed, view=self)

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.gray, row=0,
                       disabled=True)
    async def stop_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user == self.host:
            await interaction.response.defer()
            for mem in self.members:
                await self.deactivate(mem)
            self.running = False
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.mute_button.disabled = False
            self.deafen_button.disabled = False
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
                await self.leave(mem)
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
        if interaction.user == self.host:
            if len(self.members) < 2:
                await interaction.response.send_message('You are the last member.', ephemeral=True)
                return
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
        else:
            await interaction.response.send_message('Only the host can use this.', ephemeral=True)

    @discord.ui.button(label='Add', style=discord.ButtonStyle.red, row=1)
    async def add_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user == self.host:
            perms = interaction.user.guild_permissions.mute_members and interaction.user.guild_permissions.deafen_members
            add_view = AddSelector(self.server, author=interaction.user, max_value=self.max - len(self.members))
            await interaction.response.send_message('Choose who to add', view=add_view, ephemeral=True)
            await add_view.wait()
            if add_view.values:
                to_add = filter(lambda x: x not in self.members, add_view.values)
                for mem in to_add:
                    if len(self.members) < self.max:
                        if perms or not self.server.cooldowns.on_cooldown('voice_controller_add', mem):
                            await self.join(mem)
                            self.server.cooldowns.set_duration('voice_controller_add', mem, 1_60_60)

                await self.message.edit(embed=self.embed)

    @discord.ui.button(label='Change Settings:', style=discord.ButtonStyle.grey, row=2, disabled=True)
    async def settings_button(self, interaction: discord.Interaction,
                              button: discord.Button):
        ...

    @discord.ui.button(label='Mute', style=discord.ButtonStyle.red, row=2)
    async def mute_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user == self.host:
            self.mute = not self.mute
            button.style = discord.ButtonStyle.green if self.mute else discord.ButtonStyle.red
            await interaction.response.edit_message(embed=self.embed, view=self)
        else:
            await interaction.response.send_message('Only the host can change this setting.', ephemeral=True)

    @discord.ui.button(label='Deafen', style=discord.ButtonStyle.red, row=2)
    async def deafen_button(self, interaction: discord.Interaction,
                            button: discord.Button):
        if interaction.user == self.host:
            self.deafen = not self.deafen
            button.style = discord.ButtonStyle.green if self.deafen else discord.ButtonStyle.red
            await interaction.response.edit_message(embed=self.embed, view=self)
        else:
            await interaction.response.send_message('Only the host can change this setting.', ephemeral=True)


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

class AddSelector(discord.ui.View):
    def __init__(self, server: 'Server', *, min_value=1, max_value=1, author: 'discord.Member'=None, timeout=30):
        super().__init__(timeout=timeout)
        self.min_value = min_value
        self.max_value = max_value
        self.author = author
        self.channel = author.voice.channel if author.voice else None
        self.server = server
        self.values = None

        self.user_select.max_values = max_value
        self.user_select.min_values = min_value

    def get_members_in_game(self, game: str) -> list[discord.Member]:
        mems = []
        for member in self.channel.members:
            h_member = self.server.members.get(member.id)
            activity = h_member.get_game_activity()
            activity = activity.name if activity else None
            if h_member and activity == game:
                mems.append(member)
        return mems

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder='Select a user')
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        if self.author:
            if self.author != interaction.user:
                await interaction.response.send_message('You are not allowed to use this.', ephemeral=True)
                return
        self.values = select.values
        await interaction.response.edit_message(content=f'Selected: {", ".join(str(x) for x in self.values)}', view=None)
        self.stop()

    @discord.ui.button(label='Game', style=discord.ButtonStyle.green)
    async def game_button(self, interaction: discord.Interaction, button: discord.Button):
        if self.author:
            if self.author != interaction.user:
                await interaction.response.send_message('You are not allowed to use this.', ephemeral=True)
                return
        member = self.server.members.get(interaction.user.id)
        activity = member.get_game_activity()
        members = self.get_members_in_game(activity.name)
        self.values = members
        await interaction.response.edit_message(content=f'Selected: {", ".join(str(x) for x in self.values)}', view=None)
        self.stop()
