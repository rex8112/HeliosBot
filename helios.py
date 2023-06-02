import asyncio
import logging
import os
import sys

import discord
from discord.utils import setup_logging

from helios import HeliosBot, db, ServerModel, MemberModel, ChannelModel
from helios.tools import Config

logger = logging.getLogger('HeliosLogger')
logger.setLevel(logging.DEBUG)
consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)
logger.addHandler(consoleHandler)

logger2 = logging.getLogger('discord')
logger2.setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.INFO)
logger2.addHandler(consoleHandler)


description = '''The beginnings of a new Helios'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

settings = Config.from_file_path()
bot = HeliosBot(command_prefix='?', description=description, intents=intents, settings=settings)

cogs = [
    'cogs.testing_cog'
]


'''@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('-----')'''


if not bot.settings.token:
    print('Token not found, please fill out config.json.')
    sys.exit()


async def load_extensions():
    for name in os.listdir('./cogs'):
        if name.endswith('.py'):
            await bot.load_extension(f'cogs.{name[:-3]}')


async def main():
    db.connect()
    db.create_tables([ServerModel, MemberModel, ChannelModel])
    async with bot:
        setup_logging()
        await load_extensions()
        await bot.start(bot.settings.token)
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.1)
    db.close()

asyncio.run(main())
