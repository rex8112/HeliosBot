import discord

from discord.ext import commands
from tools.database import db
from tools.configLoader import settings

#intents = discord.Intents()
#intents.members = True

startup_extensions = [
    'cogs.topic',
    'cogs.quotes',
    'cogs.voice',
    'cogs.events',
    'cogs.theme',
    'cogs.gacha'
]
intents = discord.Intents.default()
intents.members = True
activity = discord.Activity(
    name='-help',
    type=discord.ActivityType.listening
)
bot = commands.Bot(
        description='A bot designed for Fun Within The Sun',
        command_prefix='-',
        activity=activity,
        intents=intents,
        owner_id=settings.owner
    )

@bot.event
async def on_ready():
    print('Logged in as')
    print('Name: {}'.format(bot.user.name))
    print('ID:   {}'.format(bot.user.id))
    print('----------')
    for guild in bot.guilds:
        print(guild.name)
        print(guild.id)
        if not db.check_server(guild):
            print('Newly Created')
        print('---------')

@bot.event
async def on_guild_join(guild):
    db.check_server(guild)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

if __name__ == "__main__":
    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print(
                'Failed to load extension {}\n{}'.format(extension, exc))

bot.run(settings.token)
