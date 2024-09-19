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

import logging
import traceback
from datetime import time, datetime
from typing import TYPE_CHECKING, Callable, Optional

import discord
from discord import app_commands, Interaction, ui
from discord.ext import commands, tasks

from helios import DynamicVoiceGroup, VoiceManager, PaginatorSelectView, Colour

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember, Server


logger = logging.getLogger('Helios.GamesCog')


class GamesCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    async def cog_unload(self) -> None:
        ...

    @app_commands.command(name='add_alias', description='Convert a separate game into an alias of another game')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(game='The game to add an alias to', alias='The game to convert into an alias')
    async def add_alias(self, interaction: discord.Interaction, game: str, alias: str):
        server = self.bot.servers.get(interaction.guild_id)
        game = await server.games.get_game(game, create_new=False)
        if game is None:
            return await interaction.response.send_message('Game not found', ephemeral=True)
        alias_game = await server.games.get_game(alias, create_new=False)
        if alias_game is None:
            return await interaction.response.send_message('Game to make alias is not found', ephemeral=True)
        if game == alias_game:
            return await interaction.response.send_message('Game and alias cannot be the same', ephemeral=True)
        await server.games.add_game_alias_from_game(game, alias_game)
        await interaction.response.send_message(f'Alias {alias} added for game {game.name}')

    @add_alias.autocomplete('game')
    async def _game_autocomplete(self, interaction: discord.Interaction, current: str):
        server = self.bot.servers.get(interaction.guild_id)
        games = server.games.games.keys()
        return [
            app_commands.Choice(name=x, value=x)
            for x in games
            if current.lower() in x.lower()
        ]

    @add_alias.autocomplete('alias')
    async def _alias_autocomplete(self, interaction: discord.Interaction, current: str):
        server = self.bot.servers.get(interaction.guild_id)
        games = server.games.games.keys()
        return [
            app_commands.Choice(name=x, value=x)
            for x in games
            if current.lower() in x.lower()
        ]


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(GamesCog(bot))
