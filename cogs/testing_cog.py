import discord

from discord import app_commands
from discord.ext import commands

TESTING_GUILD = discord.Object(id=466060673651310593)


class TestingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def guild_sync(self, ctx: commands.Context):
        self.bot.tree.copy_global_to(guild=TESTING_GUILD)
        await self.bot.tree.sync(guild=TESTING_GUILD)
        await ctx.send(f'Commands Synced to {TESTING_GUILD.id}')

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync()
        await ctx.send('Commands Synced')

    @app_commands.command(name='ping')
    async def ping_command(self, interaction: discord.Interaction):
        """ /ping """
        await interaction.response.send_message('Pong!')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TestingCog(bot))
