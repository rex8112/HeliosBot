import sys

import discord
from discord.ext import commands

from helios.tools import Config

description = '''The beginnings of a new Helios'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='?', description=description, intents=intents)
bot.settings = Config.from_file_path()


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('-----')


if not bot.settings.token:
    print('Token not found, please fill out config.json.')
    sys.exit()

bot.run(bot.settings.token)
