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

import asyncio
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from helios import VerifyView

if TYPE_CHECKING:
    from helios import HeliosBot


class VerificationCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        server = self.bot.servers.get(member.guild.id)
        helios_member = server.members.get(member.id)
        if helios_member is None:
            await asyncio.sleep(5)
            helios_member = server.members.get(member.id)

        if helios_member is None:
            return

        is_pug = await server.channels.dynamic_voice.pug_manager.check_if_pug_invite(member)
        if is_pug:
            return
        if member.guild.system_channel and not helios_member.verified:
            embed = discord.Embed(
                title=f'Verification Required for {member.name}',
                description='If you know this person please hit the button '
                            'below to give them access to the server. If '
                            'you do not know this person then please ignore '
                            'this message.\n\nIf the button is not working you'
                            ' can also use the /verify command.',
                colour=discord.Colour.orange(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            view = VerifyView(helios_member)
            await member.guild.system_channel.send(embed=embed, view=view)

            embed = discord.Embed(
                title=f'Welcome to {member.guild.name}!',
                description='This server requires a basic level of verification.'
                            ' Please wait for your friend to verify you. Alternatively, '
                            'tell the person you know in the discord to hit the Verify'
                            f' button in the {member.guild.system_channel.name} channel.',
                colour=discord.Colour.orange()
            )
            try:
                await member.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @app_commands.command(name='verify', description='An alternative to verify a new member.')
    @app_commands.guild_only()
    async def verify(self, interaction: discord.Interaction, mem: discord.Member):
        server = self.bot.servers.get(interaction.guild_id)
        requester = server.members.get(interaction.user.id)
        target = server.members.get(mem.id)
        if requester and requester.verified:
            await target.verify()
            embed = discord.Embed(
                title='Verified!',
                description=f'{target.member} is now Verified!',
                colour=discord.Colour.green()
            )
            embed.set_author(name=str(requester.member),
                             icon_url=requester.member.avatar.url)
            await interaction.response.send_message(embed=embed)
            return
        embed = discord.Embed(
            title='You are not Verified!',
            description='Please get a friend who is verified to run this '
                        'command for you.',
            colour=discord.Colour.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='verifyall',
                          description='Verify All Currently in the Server')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def verify_all(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        tasks = []
        await interaction.response.defer(ephemeral=True)
        for member in interaction.guild.members:
            helios_member = server.members.get(member.id)
            if not helios_member.verified:
                tasks.append(helios_member.verify())
        if len(tasks) > 0:
            await asyncio.gather(*tasks)
            await interaction.followup.send(f'{len(tasks)} Verified!')
        else:
            await interaction.followup.send('Everyone is already Verified!')


@app_commands.guild_only()
class PugGroup(app_commands.Group):
    ...


async def setup(bot: 'HeliosBot') -> None:
    await bot.add_cog(VerificationCog(bot))
