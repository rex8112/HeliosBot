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

import sentry_sdk
import discord
from discord.utils import setup_logging

from helios import HeliosBot, db, initialize_db
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
bot = HeliosBot(command_prefix='?', description=description, intents=intents, settings=settings)


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
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            traces_sample_rate=1.0,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            # We recommend adjusting this value in production.
            profiles_sample_rate=1.0
        )

    initialize_db()
    async with bot:
        setup_logging(root=False)
        await load_extensions()
        await bot.start(bot.settings.token)
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.1)
    db.close()

if __name__ == '__main__':
    asyncio.run(main())
