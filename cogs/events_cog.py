from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from helios.views import YesNoView

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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild.me in message.mentions and message.author.voice.channel:
            channel = message.author.voice.channel
            mention_string = ''
            allowed = []
            for m in channel.members:
                mention_string += f'{m.mention} '
                if m != message.author:
                    allowed.append(m)
            view = YesNoView(message.author)
            mess = await message.channel.send(
                f'Would you like to ping everyone in {channel.mention}?',
                view=view,
                delete_after=5
            )
            await view.wait()
            if view.value:
                await message.channel.send(mention_string, allowed_mentions=discord.AllowedMentions(users=allowed))
            else:
                try:
                    await mess.delete()
                except discord.NotFound:
                    ...


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(EventsCog(bot))
