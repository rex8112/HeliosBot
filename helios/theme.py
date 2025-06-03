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
import asyncio
from typing import TYPE_CHECKING, Callable, Optional

import discord

from .colour import Colour
from .database import ThemeModel
from .dynamic_voice import DynamicVoiceGroup

if TYPE_CHECKING:
    from .server import Server
    from .member import HeliosMember


def sorted_members(members: list['HeliosMember'], key: Callable[['HeliosMember'], int]) -> list['HeliosMember']:
    s_members = sorted(members, key=lambda x: key(x))
    s_members = filter(lambda x: not x.member.bot, s_members)
    return list(s_members)


class ThemeManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.current_theme: Optional['Theme'] = None
        self.role_map: dict['ThemeRole', discord.Role] = {}

    async def load(self):
        self.current_theme = await Theme.from_current(self.server)
        if self.current_theme:
            self.build_role_map()

    async def get_theme(self, theme_name: str) -> Optional['Theme']:
        if self.current_theme and self.current_theme.name.lower() == theme_name.lower():
            return self.current_theme
        theme = await ThemeModel.get_by_name(theme_name)
        if not theme:
            return None
        return Theme.from_db(self.server, theme)

    async def get_themes(self) -> list['Theme']:
        themes = await ThemeModel.get_all(self.server.db_entry)
        return [Theme.from_db(self.server, theme) for theme in themes]

    async def apply_theme(self, theme: 'Theme'):
        current_roles = list(self.role_map.values())
        new_role_map = {}
        to_remove = current_roles[len(theme.roles):]
        last_pos = 1
        for i, theme_role in enumerate(theme.roles):
            try:
                cur_role = current_roles[i]
            except IndexError:
                cur_role = None

            try:
                color = discord.Colour.from_str(theme_role.color)
            except ValueError:
                color = discord.Colour.dark_gray

            if cur_role:
                # Update existing role
                last_pos = cur_role.position
                await cur_role.edit(name=theme_role.name, color=color, reason='Theme Update')
            else:
                # Create new role
                cur_role = await self.server.guild.create_role(name=theme_role.name, colour=color,
                                                               permissions=discord.Permissions.none(), hoist=True,
                                                               reason='Theme Update')
                await cur_role.edit(position=last_pos, reason='Theme Update')
                last_pos = cur_role.position

            new_role_map[theme_role] = cur_role
        for role in to_remove:
            await role.delete(reason='Theme Update')

        cur_groups = self.server.channels.dynamic_voice.groups.values()
        vm = self.server.channels.dynamic_voice
        await asyncio.gather(*[vm.delete_group(group) for group in cur_groups if group not in theme.groups])
        for group in theme.groups:
            if group not in cur_groups:
                await vm.create_group_from_data(group.to_dict())
        afk_channel = self.server.guild.afk_channel
        if afk_channel and theme.afk_channel and theme.afk_channel != afk_channel.name:
            await afk_channel.edit(name=theme.afk_channel)
        await self.set_current(theme)
        await self.sort_members()

    async def set_current(self, theme: 'Theme'):
        if self.current_theme:
            self.current_theme.current = False
            self.current_theme.editable = True
            await self.current_theme.save()
        self.current_theme = theme
        self.current_theme.current = True
        self.current_theme.editable = False
        await self.current_theme.save()
        self.build_role_map()

    async def build_theme(self, roles: list[discord.Role]):
        if self.current_theme:
            self.current_theme.current = False
            await self.current_theme.save()
        self.current_theme = Theme(self.server, self.server.name,
                                   [ThemeRole(x.name, str(x.colour), len(x.members)) for x in roles])
        self.current_theme.roles[-1].maximum = -1
        await self.current_theme.save()
        self.current_theme.current = True
        self.build_role_map()
        await self.current_theme.save()

    def build_role_map(self):
        self.role_map = {}
        for t_role in self.current_theme.roles:
            d_role = discord.utils.get(self.server.guild.roles, name=t_role.name,
                                       colour=discord.Colour.from_str(t_role.color))
            self.role_map[t_role] = d_role

    async def sort_members(self):
        if not self.current_theme:
            return
        member_val, stat_name = await self.current_theme.get_sorted_members()
        members, values = zip(*member_val)
        members = list(members)
        member_role_pairs = []
        changes: list[tuple['HeliosMember', discord.Role, discord.Role]] = []
        for theme_role in self.current_theme.roles:
            role = self.role_map[theme_role]
            if not role:
                continue
            maximum = theme_role.maximum if theme_role != self.current_theme.roles[-1] else len(members)
            for i in range(maximum):
                member = members.pop(0)
                member_role_pairs.append((member, role))
        for member, role in member_role_pairs:
            old_role = None
            has_correct_roles = True
            roles = list(member.member.roles)
            for theme_role in self.current_theme.roles:
                d_role = self.role_map[theme_role]
                if d_role == role:
                    if d_role not in roles:
                        has_correct_roles = False
                        roles.append(d_role)
                else:
                    if d_role in roles:
                        has_correct_roles = False
                        roles.remove(d_role)
                        old_role = d_role
            if not has_correct_roles:
                changes.append((member, old_role, role))
                try:
                    await member.member.edit(roles=roles, reason='Theme Sort')
                except (discord.Forbidden, discord.HTTPException):
                    pass
        return changes


class Theme:
    def __init__(self, server: 'Server', name: str, roles: list['ThemeRole'], groups: list['DynamicVoiceGroup']):
        self.server = server
        self.name = name
        self.roles = roles
        self.groups = groups
        self.owner: Optional['HeliosMember'] = None
        self.editable = True
        self.current = False
        self.sort_stat = 'points'
        self.sort_type = 'total'
        self.afk_channel: str = '💤 AFK Channel'
        self.banner_url: Optional[str] = None
        self.db_entry: Optional[ThemeModel] = None

    def has_role(self, role: discord.Role):
        return any(role.name == x.name and role.colour == discord.Colour.from_str(x.color) for x in self.roles)

    async def save(self):
        if self.db_entry:
            data = self.to_dict()
            del data['owner']  # prevent synchronous access to owner
            await self.db_entry.async_update(**data)
        else:
            d = self.to_dict()
            self.db_entry = await ThemeModel.create(server=self.server.db_entry,
                                                    owner=self.owner.db_entry if self.owner else None,
                                                    name=d['name'], roles=d['roles'], groups=d['groups'])

    async def get_sorted_members(self) -> tuple[list[tuple['HeliosMember', int]], str]:
        member_value = {}
        async def fill_value(member: 'HeliosMember'):
            if self.sort_stat == 'points':
                member_value[member] = member.points
            elif self.sort_stat == 'activity':
                member_value[member] = await member.get_activity_points()

        tasks = [fill_value(member) for member in self.server.members.members.values() if not member.member.bot]
        await asyncio.gather(*tasks)
        sorted_members_list = sorted(member_value.items(), key=lambda x: x[1], reverse=True)
        return list(sorted_members_list), self.sort_stat

    @staticmethod
    def get_leaderboard_string(num: int, member: 'HeliosMember', value: int, prefix: str = ''):
        return f'{prefix:2}{num:3}. {member.member.display_name:>32}: {value:10,}\n'

    async def get_leaderboard_embeds(self, member: Optional['HeliosMember'] = None, only_member=False):
        theme = self.server.theme.current_theme
        if theme is None:
            members = [(x, x.points, i) for i, x in enumerate(list(self.server.members.members.values()))]
            leaderboard_string = self.build_leaderboard(member, members)
            p_embed = discord.Embed(
                colour=Colour.helios(),
                title=f'{self.server.guild.name} {self.server.points_name.capitalize()} Leaderboard',
                description=f'```{leaderboard_string}```'
            )
            return [p_embed]

        member_values, stat_name = await theme.get_sorted_members()
        index = 0
        embeds = []
        for role in theme.roles:
            discord_role = self.server.theme.role_map[role]
            role_members: list[tuple['HeliosMember', int, int]] = []
            member_in = False
            for i in range(role.maximum if role.maximum > 0 else len(member_values) - index):
                try:
                    if member_values[index][0] == member:
                        member_in = True
                    mem, val = member_values[index]
                    role_members.append((mem, val, index))
                    index += 1
                except IndexError:
                    break
            lb_str = self.build_leaderboard(member, role_members)
            embed = discord.Embed(
                title=discord_role.name,
                color=discord_role.color,
                description=f'```{lb_str}```'
            )
            if member_in and only_member:
                return [embed]
            embeds.append(embed)
        return embeds

    def build_leaderboard(self, author: 'HeliosMember', member_val_pos: list[tuple['HeliosMember', int, int]], ) -> str:
        leaderboard_string = ''
        user_found = False
        for mem, val, pos in member_val_pos[:10]:
            modifier = ''
            if mem == author:
                modifier = '>'
                user_found = True
            leaderboard_string += self.get_leaderboard_string(pos+1, mem, val, modifier)
        mem_only = [x[0] for x in member_val_pos]
        if not user_found and author in mem_only:
            index = mem_only.index(author)
            leaderboard_string += '...\n'
            for mem, val, i in member_val_pos[index - 1:index + 2]:
                modifier = ''
                if mem == author:
                    modifier = '>'
                leaderboard_string += self.get_leaderboard_string(i, mem, val, modifier)
        return leaderboard_string

    def to_dict(self):
        return {
            'name': self.name,
            'roles': [x.to_dict() for x in self.roles],
            'owner': self.owner.db_entry if self.owner else None,
            'groups': [x.to_dict() for x in self.groups],
            'current': self.current,
            'editable': self.editable,
            'sort_stat': self.sort_stat,
            'sort_type': self.sort_type,
            'afk_channel': self.afk_channel,
            'banner_url': self.banner_url
        }

    @classmethod
    def from_db(cls, server: 'Server', db_entry: ThemeModel):
        theme = cls(server, db_entry.name, [ThemeRole.from_dict(x) for x in db_entry.roles],
                    [DynamicVoiceGroup.from_dict(server, x) for x in db_entry.groups])
        theme.db_entry = db_entry
        theme.current = db_entry.current
        theme.editable = db_entry.editable
        theme.owner = server.members.get(db_entry.owner_id) if db_entry.owner_id else None
        theme.sort_stat = db_entry.sort_stat
        theme.sort_type = db_entry.sort_type
        theme.afk_channel = db_entry.afk_channel
        theme.banner_url = db_entry.banner_url
        return theme

    @classmethod
    async def from_id(cls, server: 'Server', theme_id: int):
        db_entry = await ThemeModel.get(id=theme_id)
        if db_entry.server != server.db_entry:
            return None
        return cls.from_db(server, db_entry)

    @classmethod
    async def from_current(cls, server: 'Server'):
        db_entry = await ThemeModel.get_current(server.db_entry)
        if not db_entry:
            return None
        return cls.from_db(server, db_entry)


class ThemeRole:
    def __init__(self, name: str, color: str, maximum: int):
        self.name = name
        self.color = color
        self.maximum = maximum
        self.icon_url: Optional[str] = None

    def _key(self):
        return self.name, self.color, self.maximum

    def __hash__(self):
        return hash(self._key())

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<ThemeRole {self.name}>'

    def to_dict(self):
        return {
            'name': self.name,
            'color': self.color,
            'maximum': self.maximum,
            'icon_url': self.icon_url
        }

    @classmethod
    def from_dict(cls, data: dict):
        role = cls(data['name'], data['color'], data['maximum'])
        role.icon_url = data.get('icon_url')
        return role
