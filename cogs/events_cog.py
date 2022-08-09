from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from helios import HeliosBot


class EventsCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        server = self.bot.servers.get(member.guild.id)
        helios_member = server.members.get(member.id)
        if not helios_member:
            server.members.add_member(member)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        server = self.bot.servers.get(guild.id)
        if not server:
            self.bot.servers.add_server(guild)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(EventsCog(bot))
