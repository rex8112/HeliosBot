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
import traceback
from typing import Optional

import discord
from discord.ext import commands

from .database import EventModel, objects
from .event_manager import EventManager
from .http import HTTPClient
from .server import Server
from .server_manager import ServerManager
from .tools import Config
from .views import TopicView, ViolationPayButton

logger = logging.getLogger('HeliosLogger')


class HeliosBot(commands.Bot):
    def __init__(self, command_prefix, *, intents, settings: Config, **options):
        self.servers = ServerManager(self)
        self.event_manager = EventManager(self, objects)
        self.settings = settings
        self.ready_once = True
        self.helios_http: Optional[HTTPClient] = None

        super().__init__(command_prefix, intents=intents, **options)

    @staticmethod
    async def add_startup(action: str, target_id: int, server: 'Server' = None) -> EventModel:
        model: EventModel = await objects.create(EventModel, action=action, target_id=target_id,
                                                 server=server.db_entry)
        return model

    @staticmethod
    async def remove_startup(model: EventModel):
        await objects.delete(model)

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
            self.ready_once = False

    @staticmethod
    async def on_slash_error(
            interaction: discord.Interaction,
            error: discord.app_commands.AppCommandError
    ):
        error_message = f'Something went wrong\n```{type(error)}: {error}```\n\nThe developer has been notified.'
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            error_message = f'You do not have permission to use this command.\n\n{error}'
        if interaction.response.is_done():
            await interaction.followup.send(error_message)
        else:
            await interaction.response.send_message(error_message, ephemeral=True)

        owner = interaction.client.get_user(180067685986467840)
        if owner and not isinstance(error, discord.app_commands.errors.MissingPermissions):
            await owner.send(f'```{traceback.format_exc()}```')
