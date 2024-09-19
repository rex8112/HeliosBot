#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
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
from datetime import datetime, time
from typing import Optional, TYPE_CHECKING

import discord
from discord.ext import tasks

from .database import GameModel, GameAliasModel

if TYPE_CHECKING:
    from .server import Server


class GameManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.games = {}
        self.alias_to_game = {}

    def start(self):
        self.manage_games.start()
        self.set_day_playtime.start()

    def stop(self):
        self.manage_games.stop()
        self.set_day_playtime.stop()

    @tasks.loop(time=time(hour=1, minute=0))
    async def set_day_playtime(self):
        await self.server.bot.wait_until_ready()
        self.games.clear()
        self.alias_to_game.clear()
        await GameModel.set_day_playtime()

    @tasks.loop(minutes=1)
    async def manage_games(self):
        await self.server.bot.wait_until_ready()
        to_update = {}
        icons = {}
        for member in self.server.members.members.values():
            game = member.get_game_activity()
            if game is None:
                continue
            if game.name in to_update:
                to_update[game.name] += 1
            else:
                to_update[game.name] = 1
            # if game.large_image_url is not None:
            #     icons[game.name] = game.large_image_url
            # elif game.small_image_url is not None:
            #     icons[game.name] = game.small_image_url
        for game in to_update:
            game = await self.get_game(game)
            await game.add_time(to_update[game.name])
            if game.name in icons:
                await game.update_icon(icons[game.name])
        now = discord.utils.utcnow()
        for game in list(self.games.values()):
            if (now - game.last_played).seconds >= 30 * 60:
                self.remove_game(game)

    async def get_game(self, name: str, *, create_new=True) -> Optional['Game']:
        if name in self.games:
            return self.games[name]
        if name in self.alias_to_game:
            return self.alias_to_game[name]
        game = await GameModel.find_game(name)
        if game is None and create_new:
            await GameModel.create_game(name, display_name=name, icon='')
            game = await GameModel.find_game(name)
        elif game is None:
            return None
        game = Game.from_db(game)
        self.add_game(game)
        return game

    def get_from_cache(self, name: str) -> Optional['Game']:
        if name in self.games:
            return self.games[name]
        if name in self.alias_to_game:
            return self.alias_to_game[name]
        return None

    async def add_game_alias_from_game(self, game: 'Game', alias: 'Game'):
        await alias.convert_to_alias_of(game)
        self.remove_game(alias)

    def add_game(self, game: 'Game'):
        self.games[game.name] = game
        for alias in game.alias:
            self.alias_to_game[alias] = game

    def remove_game(self, game: 'Game'):
        del self.games[game.name]
        for alias in game.alias:
            del self.alias_to_game[alias]


class Game:
    def __init__(self, name: str, *, display_name: str = None, icon: str = None, alias: list[str] = None,
                 play_time: int = 0, last_day_playtime: int = 0, last_played: datetime = None):
        self.name = name
        self.display_name = display_name or name
        self.alias = alias or []
        self.icon = icon
        self.play_time = play_time
        self.last_day_playtime = last_day_playtime
        self.last_played = last_played or discord.utils.utcnow()

        self.db_entry: Optional['GameModel'] = None

    async def save(self):
        if self.db_entry is None:
            self.db_entry = await GameModel.create(**self.to_dict())
        else:
            data = self.to_dict()
            del data['alias']
            await self.db_entry.async_update(**data)

        for alias in self.alias:
            await GameAliasModel.create(game=self.db_entry, alias=alias)

    async def convert_to_alias_of(self, game: 'Game'):
        await self.db_entry.delete_game()
        await game.db_entry.add_alias(self.name)
        game.play_time += self.play_time
        game.last_day_playtime += self.last_day_playtime
        game.last_played = max(game.last_played, self.last_played)
        await game.save()

    async def add_time(self, time: int):
        self.play_time += time
        await self.db_entry.add_playtime(time)

    async def set_day_playtime(self):
        self.last_day_playtime = self.play_time
        await self.db_entry.async_update(last_day_playtime=self.play_time)

    async def update_icon(self, icon: str):
        if self.icon == icon:
            return
        self.icon = icon
        await self.db_entry.async_update(icon=icon)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['name'], display_name=data.get('display_name'), icon=data.get('icon'),
                   alias=data.get('alias', []), play_time=data.get('play_time', 0),
                   last_day_playtime=data.get('last_day_playtime', 0), last_played=data.get('last_played'))

    @classmethod
    def from_db(cls, db_entry: GameModel):
        obj = cls(db_entry.name, display_name=db_entry.display_name, icon=db_entry.icon,
                  alias=[alias.alias for alias in db_entry.aliases], play_time=db_entry.play_time,
                  last_day_playtime=db_entry.last_day_playtime, last_played=db_entry.last_played)
        obj.db_entry = db_entry
        return obj

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'display_name': self.display_name,
            'icon': self.icon,
            'alias': self.alias,
            'play_time': self.play_time,
            'last_day_playtime': self.last_day_playtime,
            'last_played': self.last_played
        }

    @classmethod
    def from_activity(cls, activity: discord.Activity) -> 'Game':
        return cls(activity.name, icon=activity.large_image_url)

    def __str__(self):
        return self.display_name

    def __repr__(self):
        return f'<Game name={self.name} display_name={self.display_name}>'
