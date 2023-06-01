import discord

from discord import app_commands
from discord.ext import commands


class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, guild: discord.Member):
        ...

    @app_commands.command(name='verify', description='An alternative to verify a new member.')
    async def verify(self, interaction: discord.Interaction, mem: discord.Member):
        ...


@app_commands.guild_only()
class PugGroup(app_commands.Group):
    ...


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VerificationCog(bot))
