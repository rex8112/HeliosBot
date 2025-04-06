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

import json
import logging
from typing import TYPE_CHECKING, Dict, Optional

import discord

from .channel_manager import ChannelManager
from .cooldowns import Cooldowns
from .court import Court
from .database import ServerModel, objects
from .exceptions import IdMismatchError
from .gambling.manager import GamblingManager
from .game import GameManager
from .helios_voice_controller import HeliosVoiceController
from .member import HeliosMember
from .member_manager import MemberManager
from .shop import Shop
from .store import Store
from .theme import ThemeManager
from .tools.settings import Settings, SettingItem
from .views import VoiceControllerView

if TYPE_CHECKING:
    from .server_manager import ServerManager

logger = logging.getLogger('HeliosLogger')


class ServerSettings(Settings):
    announcement_channel = SettingItem('announcement_channel', None, discord.TextChannel,
                                       group='Misc', title='Announcement Channel',
                                       description='The channel to send announcements to.')
    archive_category = SettingItem('archive_category', None, discord.CategoryChannel,
                                   group='Topic Settings', title='Archive Category',
                                   description='The category to archive topics to.')
    topic_category = SettingItem('topic_category', None, discord.CategoryChannel,
                                 group='Topic Settings', title='Topic Category',
                                 description='The category to create topics in.')
    topic_soft_cap = SettingItem('topic_soft_cap', 10, int,
                                 group='Topic Settings', title='Topic Soft Cap',
                                 description='The number of topics a server can have before it tries to archive.')
    voice_controller = SettingItem('voice_controller', None, discord.Role,
                                   group='Misc', title='In Game Voice Controller Role',
                                   description='The role that signifies a user is in a voice controlled state.')
    verified_role = SettingItem('verified_role', None, discord.Role,
                                group='Misc', title='Verified Role',
                                description='The role that signifies a user has been verified.')
    partial = SettingItem('partial', 4, int,
                          group='Points', title='Lonely Coefficient',
                          description='The number of minutes it takes to earn a point when alone.')
    points_per_minute = SettingItem('points_per_minute', 1, int,
                                    group='Points', title='Points Per Minute',
                                    description='The number of points a user earns per minute.')
    points_name = SettingItem('points_name', 'mins', str,
                              group='Points', title='Points Name',
                              description='The name of the points.')
    private_create = SettingItem('private_create', None, discord.VoiceChannel)
    dynamic_voice_category = SettingItem('dynamic_voice_category', None, discord.CategoryChannel,
                                         group='Dynamic Voice', title='Dynamic Voice Category',
                                         description='The category to create dynamic voice channels in.')
    mute_points_per_second = SettingItem('mute_points_per_second', 1, int,
                                         group='Shop', title='Mute: Points Per Second',
                                         description='The number of points it costs to mute someone per second.')
    mute_seconds_per_increase = SettingItem('mute_seconds_per_increase', 60, int,
                                            group='Shop', title='Mute: Seconds Per Increase',
                                            description='The number of seconds it takes to increase the mute cost.')
    music_points_per_minute = SettingItem('music_points_per_minute', 2, int,
                                          group='Music', title='Music: Points Per Minute',
                                          description='The number of points it costs to play music per minute.')
    deafen_points_per_second = SettingItem('deafen_points_per_second', 1, int,
                                           group='Shop', title='Deafen: Points Per Second',
                                           description='The number of points it costs to deafen someone per second.')
    deafen_seconds_per_increase = SettingItem('deafen_seconds_per_increase', 30, int,
                                              group='Shop', title='Deafen: Seconds Per Increase',
                                              description='The number of seconds it takes to increase the deafen cost.')
    shield_points_per_hour = SettingItem('shield_points_per_hour', 100, int,
                                         group='Shop', title='Shield: Points Per Second',
                                         description='The number of points it costs to shield someone per hour.')
    deflector_points_per_hour = SettingItem('shield_points_per_hour', 200, int,
                                            group='Shop', title='Deflector: Points Per Second',
                                            description='The number of points it costs to put a deflector on per hour.')
    channel_shield_points_per_hour = SettingItem('channel_shield_points_per_hour', 300, int,
                                                 group='Shop', title='Channel Shield: Points Per Second',
                                                 description='The number of points it costs to shield a channel per '
                                                             'hour.')

    gambling_category = SettingItem('gambling_category', None, discord.CategoryChannel,
                                    group='Misc', title='Gambling Category',
                                    description='The category to create gambling channels in.')

    transfer_tax = SettingItem('transfer_tax', 0.10, float,
                               group='Shop', title='Transfer Tax',
                               description='The percentage of points taken when transferring points.')

    daily_store_refreshes = SettingItem('daily_store_refreshes', 1, int,
                                        group='Shop', title='Daily Store Refreshes',
                                        description='The number of times the store refreshes daily.')
    inactive_admin = SettingItem('inactive_admin', None, discord.Role,
                                 group='Admin', title='Inactive Admin Role',
                                    description='The role that signifies a user is an admin and can toggle powers.')
    active_admin = SettingItem('active_admin', None, discord.Role,
                                 group='Admin', title='Active Admin Role',
                                 description='The role that signifies a user currently has admin powers.')


class Server:
    def __init__(self, manager: 'ServerManager', guild: discord.Guild):
        self.loaded = False
        self.bot = manager.bot
        self.guild = guild
        self.manager = manager
        self.channels = ChannelManager(self)
        self.members = MemberManager(self)
        self.shop = Shop(self.bot)
        self.store: Optional['Store'] = None
        self.court = Court(self)
        self.voice_controller = HeliosVoiceController(self)
        self.topics = {}
        self.voice_controllers: list['VoiceControllerView'] = []
        self.settings = ServerSettings(self.bot)
        self.theme = ThemeManager(self)
        self.gambling = GamblingManager(self)
        self.games = GameManager(self)
        self.cooldowns = Cooldowns()
        self.flags = []

        self._new = False
        self._save_task = None
        self.db_entry = None

    # Properties
    @property
    def name(self):
        return self.guild.name

    @property
    def id(self):
        return self.guild.id

    @property
    def db_id(self):
        return self.db_entry.id

    @property
    def private_create_channel(self) -> Optional[discord.VoiceChannel]:
        return self.settings.private_create.value

    @property
    def voice_controller_role(self) -> Optional[discord.Role]:
        roles = self.guild.roles
        for role in roles:
            if role.name == 'VoiceControlled':
                return role

    @property
    def verified_role(self) -> Optional[discord.Role]:
        role = self.settings.verified_role.value
        if role is None:
            self.settings.verified_role = None
        return role

    @property
    def points_name(self) -> str:
        return self.settings.points_name.value

    @property
    def me(self) -> 'HeliosMember':
        return self.members.get(self.bot.user.id)

    @property
    def announcement_channel(self) -> Optional[discord.TextChannel]:
        return self.settings.announcement_channel.value

    @classmethod
    def new(cls, manager: 'ServerManager', guild: discord.Guild):
        s = cls(manager, guild)
        s._new = True
        s.loaded = True
        return s

    async def setup(self, data: Optional['ServerModel']):
        if self._new or data is None:
            logger.debug(f'Setting up new server {self.name}')
            await self.members.setup()
            await self.channels.setup()
            await self.save()
        else:
            logger.debug(f'Setting up server {self.name}')
            self.deserialize(data)
            await self.members.setup(data.members)
            await self.channels.setup(data.channels)
        await self.theme.load()
        self.store = await Store.from_server(self)

        role = self.voice_controller_role
        if role is None:
            return
        for member in role.members:
            h_member = self.members.get(member.id)
            await h_member.voice_unmute_undeafen(reason='VoiceControlled Cleanup')
            await member.remove_roles(role)

        self.start()
        logger.debug(f'Server {self.name} setup complete')

    async def shutdown(self):
        self.stop()
        await self.save()

    def start(self):
        logger.debug(f'Starting server {self.name}')
        self.games.start()
        self.store.start()
        self.voice_controller.start()

    def stop(self):
        logger.debug(f'Stopping server {self.name}')
        self.games.stop()
        self.store.stop()
        self.voice_controller.stop()

    # Methods
    def deserialize(self, data: ServerModel) -> None:
        """
        Takes a dictionary from the Helios API and fills out the class
        :param data: A JSON Dictionary from the Helios API
        :raises helios.IdMismatchError: When the ID in the data does not equal the ID in the given guild
        """
        if data.id != self.id:
            raise IdMismatchError('ID in data does not match server ID', self.id, data.id)
        self.flags = json.loads(data.flags)
        self.settings.load_dict(json.loads(data.settings))
        self.db_entry = data
        self.loaded = True

    def serialize(self) -> Dict:
        """
        Returns a JSON Serializable object.
        :return: A JSON Serializable object
        """
        data = {
            'id': self.id,
            'name': self.name,
            'settings': json.dumps(self.settings.to_dict()),
            'flags': json.dumps(self.flags)
        }

        return data

    async def add_on_voice(self, member: 'HeliosMember', action: str):
        return await self.bot.event_manager.add_action('on_voice', member, action)

    def queue_save(self):
        if self._save_task:
            return
        self._save_task = self.bot.loop.create_task(self.save())

    async def save(self):
        try:
            if self._new:
                self.db_entry = objects.create(ServerModel, **self.serialize())
                self._new = False
            else:
                self.db_entry.update_model_instance(self.db_entry, self.serialize())
                await objects.update(self.db_entry)
        finally:
            self._save_task = None

    async def do_on_voice(self, helios_member: 'HeliosMember'):
        if helios_member.allow_on_voice is False:
            return
        member: discord.Member = helios_member.member
        actions = await self.bot.event_manager.get_actions('on_voice', helios_member)
        edits = {}
        for action in actions:
            if action.action == 'unmute':
                edits['mute'] = False
            elif action.action == 'mute':
                edits['mute'] = True
            if action.action == 'undeafen':
                edits['deafen'] = False
            elif action.action == 'deafen':
                edits['deafen'] = True
        if len(edits) > 0:
            try:
                await member.edit(**edits)
                await self.bot.event_manager.clear_actions('on_voice', helios_member)
                await self.save()
            except (discord.Forbidden, discord.HTTPException):
                ...
