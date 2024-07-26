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
import io
import logging
import random
import traceback
from typing import Optional

import discord
from discord.ext import commands, tasks
from aiohttp import ClientSession

from .database import EventModel, objects
from .effects import EffectsManager
from .event_manager import EventManager
from .http import HTTPClient
from .server import Server
from .server_manager import ServerManager
from .tools import Config
from .views import ViolationPayButton

logger = logging.getLogger('HeliosLogger')


class HeliosBot(commands.Bot):
    def __init__(self, command_prefix, *, intents, settings: Config, **options):
        self.servers = ServerManager(self)
        self.event_manager = EventManager(self, objects)
        self.effects = EffectsManager(self)
        self.settings = settings
        self.ready_once = True
        self.helios_http: Optional[HTTPClient] = None
        self._session: Optional[ClientSession] = None
        self.activities: list[str] = []

        self._last_activity = None

        super().__init__(command_prefix, intents=intents, **options)

    @staticmethod
    async def add_startup(action: str, target_id: int, server: 'Server' = None) -> EventModel:
        model: EventModel = await objects.create(EventModel, action=action, target_id=target_id,
                                                 server=server.db_entry)
        return model

    @staticmethod
    async def remove_startup(model: EventModel):
        await objects.delete(model)

    def add_activity(self, activity: str):
        self.activities.append(activity)

    def remove_activity(self, activity: str):
        self.activities.remove(activity)

    def get_helios_member(self, identifier: str):
        values = identifier.split('.')
        server = self.servers.get(int(values[2]))
        return server.members.get(int(values[1])) if server is not None else None

    def get_session(self):
        if not self._session:
            self._session = ClientSession()
        return self._session

    async def setup_hook(self) -> None:
        self.tree.on_error = self.on_slash_error
        self.helios_http = HTTPClient(
            self.settings.api_url,
            loop=self.loop,
            api_username=self.settings.api_username,
            api_password=self.settings.api_password,
            name_api_key=self.settings.randomname_api_key
        )
        self.add_dynamic_items(ViolationPayButton)

    async def run_startup_actions(self):
        rem_actions = []
        res = await self.event_manager.get_all_trigger_actions('on_start')
        for r in res:
            if r.action == 'delete_channel':
                try:
                    c = self.get_channel(r.target_id)
                    if c:
                        await c.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    ...
                rem_actions.append(self.event_manager.delete_action(r))
        await asyncio.gather(*rem_actions)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        if self.ready_once:
            logger.debug('Beginning server load')
            logger.debug('Running startup actions')
            await self.run_startup_actions()
            logger.debug('Running server setup')
            await self.servers.setup()
            logger.debug('Starting effects manager')
            _ = self.loop.create_task(self.effects.manage_effects())
            await self.effects.fetch_all()
            self.check_activity.start()
            logger.debug('Finished setup')
            self.ready_once = False

    async def on_disconnect(self):
        if self._session:
            await self._session.close()
            self._session = None

    @tasks.loop(minutes=5)
    async def check_activity(self):
        if len(self.activities) > 1:
            new_activity = self._last_activity
            while new_activity == self._last_activity:
                new_activity = random.choice(self.activities)
            await self.change_presence(activity=discord.CustomActivity(name=new_activity))
            self._last_activity = new_activity
        elif len(self.activities) == 1:
            if self.activity.name != self.activities[0]:
                await self.change_presence(activity=discord.CustomActivity(name=self.activities[0]))
                self._last_activity = self.activities[0]
        else:
            if self.activity:
                await self.change_presence(activity=None)
                self._last_activity = None

    @staticmethod
    async def on_slash_error(
            interaction: discord.Interaction,
            error: discord.app_commands.AppCommandError
    ):
        error_message = (f'Something unexpected went wrong\n```{type(error)}: {error}```\n\n'
                         f'The developer has been notified.')
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            error_message = f'You do not have permission to use this command.\n\n{error}'
        if interaction.response.is_done():
            await interaction.followup.send(error_message)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)

        owner = interaction.client.get_user(180067685986467840)
        string_io = io.BytesIO(traceback.format_exc().encode())
        if owner and not isinstance(error, discord.app_commands.errors.MissingPermissions):
            await owner.send(f'{interaction.user} encountered an error while using a command in {interaction.channel}\n'
                             f'\n{interaction.command.qualified_name} : {interaction.command.parameters}',
                             file=discord.File(string_io, filename='error.txt'))

    async def report_error(self, error, custom_msg=''):
        owner = self.get_user(180067685986467840)
        if owner and not isinstance(error, discord.app_commands.errors.MissingPermissions):
            await owner.send(
                f'{custom_msg}\n'
                f'```{traceback.format_exc()}```')
