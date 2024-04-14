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

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from ..member import HeliosMember

__all__ = ('VerifyView',)


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
