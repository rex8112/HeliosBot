from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from helios.tools.views import YesNoView

if TYPE_CHECKING:
    from helios import HeliosBot


class EventsCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        server = self.bot.servers.get(member.guild.id)
        helios_member = await server.members.fetch(member.id)
        if not helios_member:
            await server.members.add_member(member)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        server = self.bot.servers.get(guild.id)
        if not server:
            self.bot.servers.add_server(guild)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if message.guild.me in message.mentions and message.author.voice:
            if not message.author.voice.channel:
                return
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

    @commands.Cog.listener()
    async def on_voice_state_update(self,
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState
                                    ):
        server = self.bot.servers.get(member.guild.id)
        helios_member = server.members.get(member.id)
        role = server.voice_controller_role
        if after.channel is None:
            return
        if before.channel is not None:
            return

        await server.do_on_voice(helios_member)

        if role is None:
            return
        if role in member.roles:
            fix = True
            for controller in server.voice_controllers:
                if member in controller.members:
                    fix = False
            if fix:
                await member.edit(mute=False, deafen=False)
                await member.remove_roles(role)
                await member.send('Noticed you might have still been muted/deafened from last time you used the ingame '
                                  'voice controller. I went ahead and fixed it, make sure you press Leave next time.')


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(EventsCog(bot))
