import discord

from discord.ext import tasks, commands

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title='Command on Cooldown',
                description=f'Try again in **{error.retry_after}** seconds',
                colour=discord.Colour.red()
            )
        elif isinstance(error, commands.MaxConcurrencyReached):
            embed = discord.Embed(
                title='Max Concurrency Reached',
                description=f'Only **{error.number}** instance(s) of this command per {error.per}.',
                colour=discord.Colour.red()
            )
        elif isinstance(error, commands.NoPrivateMessage):
            embed = discord.Embed(title='No Private Message', colour=discord.Colour.red(), description='Sorry. This command is not allow in private messages. Run {}help to see what is supported in DMs'.format(self.bot.CP))
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.CheckFailure):
            embed = discord.Embed(title='Check Failure', colour=discord.Colour.red(), description='{}'.format(error))
        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            embed = discord.Embed(title='Incomplete Arguments', colour=discord.Colour.red(), description='{}: {}'.format(type(error).__name__, str(error)))
        else:
            print('{}: {}'.format(type(error).__name__, error))
            embed = discord.Embed(title="Unknown Error Detected", colour=discord.Colour.red(), description='**Error Details**```{}: {}```'.format(type(error).__name__, str(error)))
            embed.set_footer(text='I have already notified the programmer.')
            owner_embed = discord.Embed(title='Error In Command: {}'.format(ctx.command.name), colour=discord.Colour.red(), description='```{}: {}```'.format(type(error).__name__, str(error)))
            owner_embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
            owner = self.bot.get_user(self.bot.owner_id)
            if ctx.author != owner and owner:
                await owner.send(embed=owner_embed)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Events(bot))