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
from discord import app_commands
from discord.ext import commands

from helios import VoiceControllerView

if TYPE_CHECKING:
    from helios import HeliosBot


class VoiceControllerCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='ingame', description='Run a voice controller to aid for in game VC')
    async def voice_controller(
            self,
            interaction: discord.Interaction,
            name: str,
            maximum: int,
            mute: bool = False,
            deafen: bool = True,
            allow_dead: bool = True
    ):
        server = self.bot.servers.get(interaction.guild_id)
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
        view.message = await interaction.response.send_message(embed=view.embed, view=view)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(VoiceControllerCog(bot))
