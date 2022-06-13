import sys

import discord
from discord.ext import commands

from helios import HeliosBot
from helios.server import Server
from helios.tools import Config

description = '''The beginnings of a new Helios'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

settings = Config.from_file_path()
bot = HeliosBot(command_prefix='?', description=description, intents=intents, settings=settings)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('-----')

    for guild in bot.guilds:
        server = Server(bot, 'None', guild)
        await server.setup_hook()


if not bot.settings.token:
    print('Token not found, please fill out config.json.')
    sys.exit()

if __name__ == '__main__':
    bot.run(bot.settings.token)
