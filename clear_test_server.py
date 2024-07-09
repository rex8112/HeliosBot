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
from discord.ext import commands
from discord.utils import setup_logging

from helios import db
from helios.tools import Config

logger = logging.getLogger('HeliosLogger')
logger.setLevel(logging.DEBUG)
consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)
fileHandler = logging.FileHandler('helios.log', mode='a')
fileHandler.setLevel(logging.WARN)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
consoleHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)
logger.addHandler(fileHandler)


description = '''The beginnings of a new Helios'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

settings = Config.from_file_path()
settings.save()
bot = commands.Bot(command_prefix='?', description=description, intents=intents)


'''@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('-----')'''


if not settings.token:
    print('Token not found, please fill out config.json.')
    sys.exit()


async def load_extensions():
    for name in os.listdir('./cogs'):
        if name.endswith('.py'):
            await bot.load_extension(f'cogs.{name[:-3]}')

@bot.event
async def on_ready():
    guild = bot.get_guild(466060673651310593)
    for category, channel in guild.by_category():
        keep = ['text channels', 'voice channels']
        if category is not None and category.name.lower() in keep:
            continue
        [await x.delete() for x in channel]
        if category:
            await category.delete()
    await bot.close()

async def main():
    async with bot:
        setup_logging(root=False)
        await load_extensions()
        await bot.start(settings.token)
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.1)
    db.close()

if __name__ == '__main__':
    asyncio.run(main())
