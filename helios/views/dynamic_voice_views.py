#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
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
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord import ui, ButtonStyle, Interaction, Color, Embed

from .generic_views import VoteView, YesNoView
from ..colour import Colour
from ..modals import VoiceNameChange
from .shop_view import ShopView
from .voice_view import VoiceControllerView

if TYPE_CHECKING:
    from ..dynamic_voice import DynamicVoiceChannel

__all__ = ('DynamicVoiceView', 'PrivateVoiceView')


class DynamicVoiceView(ui.View):
    def __init__(self, voice: 'DynamicVoiceChannel'):
        super().__init__(timeout=None)
        self.voice = voice
        self.dynamic_split.disabled = True

    def get_embed(self):
        embed = Embed(
            title=f'{self.voice.channel.name}',
            color=Color.blurple()
        )
        embed.add_field(name='Shop', value='Open a Shop')
        embed.add_field(name='Game Controller', value='Open a Game Controller to control mutes for in game voice chat.')
        embed.add_field(name='Split', value='Split the channel into two separate channels.')
        embed.add_field(name='Private', value='Make the channel private.')
        return embed

    @ui.button(label='Shop', style=ButtonStyle.blurple)
    async def dynamic_shop(self, interaction: Interaction, button: ui.Button):
        server = self.voice.bot.servers.get(interaction.guild_id)
        embed = discord.Embed(
            title=f'{interaction.guild.name} Shop',
            colour=Colour.helios(),
            description='Available Items'
        )
        [embed.add_field(name=x.name, value=x.desc, inline=False) for x in server.shop.items]
        view = ShopView(server)
        await interaction.response.send_message(embed=embed, view=view)

    @ui.button(label='Game Controller', style=ButtonStyle.blurple)
    async def dynamic_game_controller(self, interaction: Interaction, button: ui.Button):
        if interaction.user not in self.voice.channel.members:
            await interaction.response.send_message(content='You are not in the channel.', ephemeral=True)
            return
        modal = GameControllerModal()
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        name = modal.name
        maximum = modal.maximum
        mute = modal.mute
        deafen = modal.deafen
        allow_dead = modal.allow_dead

        server = self.voice.bot.servers.get(interaction.guild_id)
        role = server.voice_controller_role
        if role is None:
            await server.guild.create_role(name='VoiceControlled', permissions=discord.Permissions.none())
        member = await server.members.fetch(interaction.user.id)
        if member.member.voice:
            channel = member.member.voice.channel
        else:
            return
        view = VoiceControllerView(server, channel, name=name, maximum=maximum, allow_dead=allow_dead)
        view.mute = mute
        view.deafen = deafen
        await view.join(member.member)
        view.message = await interaction.channel.send(embed=view.embed, view=view)

    @ui.button(label='Split', style=ButtonStyle.blurple)
    async def dynamic_split(self, interaction: Interaction, button: ui.Button):
        ...

    @ui.button(label='Private', style=ButtonStyle.red)
    async def dynamic_private(self, interaction: Interaction, button: ui.Button):
        member = self.voice.server.members.get(interaction.user.id)
        # If member is in the channel, try to convert current channel to private.
        if member.member in self.voice.channel.members:
            # If member has the ability to move members, make the channel private without a vote.
            if self.voice.channel.permissions_for(member.member).move_members or len(self.voice.channel.members) == 1:
                await self.voice.make_private(member)
                await interaction.followup.send(f'{self.voice.channel.mention} set to private.')
                await self.voice.update_control_message(force=True)
            else:
                # Vote Process
                embed = Embed(title='Vote to Make Channel Private',
                              description='Would you like to make this channel private?\n'
                                          '**Vote Expires in 30 seconds.**',
                              color=Color.blurple())
                view = VoteView(set(self.voice.channel.members), time=30)
                mentions = ' '.join([m.mention for m in self.voice.channel.members])
                await interaction.response.send_message(content=mentions, embed=embed, view=view)
                message = await interaction.original_response()
                await view.wait()
                if view.get_result():
                    await message.edit(content='Vote Passed', view=None, embed=None, delete_after=10)
                    await self.voice.make_private(member)
                    await self.voice.update_control_message(force=True)
                else:
                    await message.edit(content='Vote Failed', view=None, embed=None, delete_after=10)
        else:
            await interaction.response.defer(thinking=True, ephemeral=True)
            channel = await self.voice.manager.get_inactive_channel()
            await channel.make_private(member)
            await interaction.followup.send(f'{channel.channel.mention} created and set to private.')


class GameControllerModal(ui.Modal, title='Game Controller Settings'):
    name = ui.TextInput(label='Name', required=True)
    maximum = ui.TextInput(label='Maximum', required=True)
    mute = ui.TextInput(label='Mute', required=True, default='False')
    deafen = ui.TextInput(label='Deafen', required=True, default='True')
    allow_dead = ui.TextInput(label='Allow Dead', required=True, default='True')

    def __init__(self, *, timeout=30):
        super().__init__(timeout=timeout)

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            self.name = self.name.value
            self.maximum = int(self.maximum.value)
            self.mute = self.mute.value.lower() == 'true'
            self.deafen = self.deafen.value.lower() == 'true'
            self.allow_dead = self.allow_dead.value.lower() == 'true'
        except ValueError:
            await interaction.response.send_message(
                'You must provide an actual number.',
                ephemeral=True
            )
            return
        await interaction.response.defer()
        self.stop()


class PrivateVoiceView(DynamicVoiceView):
    def __init__(self, voice: 'DynamicVoiceChannel'):
        super().__init__(voice)
        self.remove_item(self.dynamic_private)
        if self.voice.template.private:
            self.whitelist.disabled = True
        else:
            self.blacklist.disabled = True

    def get_embed(self) -> discord.Embed:
        owner = self.voice.h_owner
        template = self.voice.template
        owner_string = ''
        if owner:
            owner_string = f'Owner: {owner.member.mention}'
        private_string = ('This channel **is** visible to everyone except '
                          'those in Denied')
        if template.private:
            private_string = ('This channel **is __not__** visible to anyone '
                              'except admins and those in Allowed')
        embed = discord.Embed(
            title=f'{template.name if template else self.voice.channel.name} Menu',
            description=('Any and all settings are controlled from this '
                         'message.\n'
                         f'{owner_string}\n\n{private_string}'),
            colour=discord.Colour.blurple()
        )
        allowed_string = '\n'.join(x.mention
                                   for x in template.allowed.values())
        denied_string = '\n'.join(x.mention
                                  for x in template.denied.values())
        embed.add_field(
            name='Allowed',
            value=allowed_string if allowed_string else 'None'
        )
        embed.add_field(
            name='Denied',
            value=denied_string if denied_string else 'None'
        )
        return embed

    @ui.button(label='Public', style=ButtonStyle.red)
    async def dynamic_public(self, interaction: Interaction, _: ui.Button):
        member = self.voice.server.members.get(interaction.user.id)
        if member.member not in self.voice.channel.members:
            await interaction.response.send_message(content='You are not in the channel.', ephemeral=True)
            return
        if self.voice.name_on_cooldown():
            await interaction.response.send_message(content='Can not change to public while name is on cooldown.',
                                                    ephemeral=True)
            return
        # If member is the owner or has the ability to move members, make the channel public without a vote.
        if self.voice.owner == interaction.user or self.voice.channel.permissions_for(member.member).move_members:
            group = list(self.voice.manager.groups.values())[0]
            await interaction.response.defer(thinking=True, ephemeral=True)
            await self.voice.make_active(group)
            await self.voice.update_control_message(force=True)
            await interaction.followup.send(content='Channel is now public.')
            return
        # Start Vote Process
        embed = Embed(title='Vote to Make Channel Public',
                      description='Would you like to make this channel public?\n'
                                  '**Vote Expires in 30 seconds.**',
                      color=Color.blurple())
        view = VoteView(set(self.voice.channel.members), time=30)
        mentions = ' '.join([m.mention for m in self.voice.channel.members])
        await interaction.response.send_message(content=mentions, embed=embed, view=view)
        message = await interaction.original_response()
        await view.wait()
        if view.get_result():
            await message.edit(content='Vote Passed', view=None, embed=None, delete_after=10)
            group = list(self.voice.manager.groups.values())[0]
            await self.voice.make_active(group)
            await self.voice.update_control_message(force=True)
        else:
            await message.edit(content='Vote Failed', view=None, embed=None, delete_after=10)

    @ui.button(label='Change Name', style=discord.ButtonStyle.gray,
               custom_id='voice:name', row=1)
    async def change_name(self, interaction: discord.Interaction,
                          _: ui.Button):
        voice: 'DynamicVoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        now = datetime.now().astimezone()
        await interaction.response.send_modal(VoiceNameChange(voice))

    @ui.button(label='Make Private', style=discord.ButtonStyle.green, row=1)
    async def whitelist(self, interaction: discord.Interaction,
                        _: ui.Button):
        voice: 'DynamicVoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        template = voice.template
        template.private = True
        await interaction.response.defer()
        await voice.apply_template(template)
        await voice.update_control_message(force=True)
        await template.save()

    @ui.button(label='Make Public', style=discord.ButtonStyle.red, row=1)
    async def blacklist(self, interaction: discord.Interaction,
                        _: ui.Button):
        voice: 'DynamicVoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        template = voice.template
        template.private = False
        await interaction.response.defer()
        await voice.apply_template(template)
        await voice.update_control_message(force=True)
        await template.save()

    @ui.button(label='Templates', row=1)
    async def templates(self, interaction: discord.Interaction, _: ui.Button):
        if self.voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        view = TemplateView(self.voice)
        await interaction.response.send_message(content='Templates', view=view, ephemeral=True)

    @ui.select(cls=ui.UserSelect, placeholder='Add to Allowed')
    async def allow_user(self, interaction: discord.Interaction, select: ui.UserSelect):
        voice: 'DynamicVoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        member = select.values[0]
        await interaction.response.defer(thinking=True, ephemeral=True)
        template = self.voice.template
        template.allow(member)
        await self.voice.apply_template(template)
        await template.save()
        await self.voice.update_control_message(force=True)
        await interaction.followup.send(f'{member.mention} Allowed in '
                                        f'{self.voice.channel.mention}.')

    @ui.select(cls=ui.UserSelect, placeholder='Add to Denied')
    async def deny_user(self, interaction: discord.Interaction, select: ui.UserSelect):
        voice: 'DynamicVoiceChannel' = self.voice
        if voice.owner != interaction.user:
            await interaction.response.send_message(
                'You are not allowed to edit this channel.',
                ephemeral=True
            )
            return
        member = select.values[0]
        await interaction.response.defer(thinking=True, ephemeral=True)
        template = self.voice.template
        template.deny(member)
        await self.voice.apply_template(template)
        await template.save()
        await self.voice.update_control_message(force=True)
        await interaction.followup.send(f'{member.mention} Denied in '
                                        f'{self.voice.channel.mention}.')


class TemplateView(ui.View):
    def __init__(self, voice: 'DynamicVoiceChannel'):
        super().__init__()
        self.voice = voice
        self.owner = self.voice.h_owner
        self.templates = self.voice.h_owner.templates
        self.new_template_button.label = 'New Template' if self.voice.template.is_stored() else 'Save Current Template'
        self.refresh_select()

    def refresh_select(self):
        self.select_template.options.clear()
        if len(self.templates) > 1:
            self.select_template.disabled = False
            for template in self.templates[1:]:
                self.select_template.add_option(label=template.name)
        else:
            self.select_template.disabled = True
            self.select_template.add_option(label='Nothing')

    def get_embed(self):
        template = self.templates[0]
        embed = discord.Embed(
            title='Currently Selected Template',
            description=f'Template: {template.name}\nPrivate: {template.private}',
            colour=discord.Colour.orange()
        )
        allowed_string = '\n'.join(x.mention
                                   for x in template.allowed.values())
        denied_string = '\n'.join(x.mention
                                  for x in template.denied.values())
        embed.add_field(
            name='Allowed',
            value=allowed_string if allowed_string else 'None'
        )
        embed.add_field(
            name='Denied',
            value=denied_string if denied_string else 'None'
        )
        return embed

    def get_template(self, name: str):
        for template in self.templates:
            if template.name.lower() == name.lower():
                return template
        return None

    def new_template(self):
        temp = self.voice.h_owner.create_template()
        self.templates.remove(temp)
        self.templates.insert(0, temp)
        return temp

    def switch_template(self, index: int):
        temp = self.templates.pop(index)
        self.templates.insert(0, temp)

    async def save(self):
        await self.owner.save(force=True)

    @discord.ui.select(placeholder='Select Template')
    async def select_template(self, interaction: discord.Interaction, select: discord.ui.Select):
        temp = self.get_template(select.values[0])
        index = self.templates.index(temp)
        self.switch_template(index)
        await interaction.response.edit_message(content='Applying Template...', embed=None, view=None)
        await self.voice.apply_template(temp)
        await self.voice.update_control_message(force=True)
        await self.save()
        self.stop()

    @discord.ui.button(label='New Template', style=discord.ButtonStyle.green)
    async def new_template_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.voice.template.is_stored():
            temp = self.new_template()
            await interaction.response.edit_message(content='Applying Template...', embed=None, view=None)
            await self.voice.apply_template(temp)
            await self.voice.update_control_message(force=True)
        else:
            await interaction.response.edit_message(content='Adding Current Template...', embed=None, view=None)
            self.templates.insert(0, self.voice.template)
        await self.save()
        self.stop()

    @discord.ui.button(label='Delete Current Template', style=discord.ButtonStyle.red)
    async def delete_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        temp = self.templates[0]
        view = YesNoView(self.owner.member, timeout=15)
        embed = discord.Embed(
            title=f'Delete {temp.name}?',
            colour=discord.Colour.red(),
            description='This action can not be undone!'
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()
        if view.value:
            self.templates.pop(0)
            if len(self.templates) == 0:
                self.new_template()
            await interaction.edit_original_response(content='Applying Template...', embed=None, view=None)
            try:
                await interaction.message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                ...
            await self.voice.apply_template(self.templates[0])
            await self.voice.update_control_message(force=True)
            await self.save()
            self.stop()
