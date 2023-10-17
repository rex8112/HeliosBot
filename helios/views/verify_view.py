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
