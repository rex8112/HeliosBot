#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import asyncio
import logging
import os
import sys

import discord
from discord.utils import setup_logging

from helios import HeliosBot, db, initialize_db
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
    initialize_db()
    async with bot:
        setup_logging()
        await load_extensions()
        await bot.start(bot.settings.token)
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.1)
    db.close()

asyncio.run(main())
