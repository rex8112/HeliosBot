from typing import TYPE_CHECKING, Optional

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
