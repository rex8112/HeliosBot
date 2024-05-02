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
from typing import TYPE_CHECKING

import discord
from discord import ui, ButtonStyle, Interaction, Color, Embed

from .generic_views import VoteView

if TYPE_CHECKING:
    from ..dynamic_voice import DynamicVoiceChannel


class DynamicVoiceView(ui.View):
    def __init__(self, voice: 'DynamicVoiceChannel'):
        super().__init__(timeout=None)
        self.voice = voice
        self.dynamic_shop.disabled = True
        self.dynamic_game_controller.disabled = True
        self.dynamic_split.disabled = True

    def get_embed(self):
        ...

    @ui.button(label='Shop', style=ButtonStyle.blurple)
    async def dynamic_shop(self, interaction: Interaction, button: ui.Button):
        ...

    @ui.button(label='Game Controller', style=ButtonStyle.blurple)
    async def dynamic_game_controller(self, interaction: Interaction, button: ui.Button):
        ...

    @ui.button(label='Split', style=ButtonStyle.blurple)
    async def dynamic_split(self, interaction: Interaction, button: ui.Button):
        ...

    @ui.button(label='Private', style=ButtonStyle.blurple)
    async def dynamic_private(self, interaction: Interaction, button: ui.Button):
        member = self.voice.server.members.get(interaction.user.id)
        # If member is in the channel, try to convert current channel to private.
        if member.member in self.voice.channel.members:
            # If member has the ability to move members, make the channel private without a vote.
            if self.voice.channel.permissions_for(member.member).move_members:
                await self.voice.make_private(member)
            else:
                # TODO: Vote Process
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
                else:
                    await message.edit(content='Vote Failed', view=None, embed=None, delete_after=10)
        else:
            channel = await self.voice.manager.get_inactive_channel()
            await channel.make_private(member)


class PrivateVoiceView(ui.View):
    def __init__(self, voice: 'DynamicVoiceChannel'):
        super().__init__(timeout=None)
        self.voice = voice

