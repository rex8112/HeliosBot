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
from typing import TYPE_CHECKING, Callable, Optional

import discord
from discord import ui, ButtonStyle, Interaction

from .database import ThemeModel

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

    async def apply_theme(self, theme: 'Theme'):
        current_roles = list(self.role_map.values())
        new_role_map = {}
        to_remove = current_roles[len(theme.roles):]
        last_pos = max(x.position for x in self.server.guild.roles)
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
                await cur_role.edit(position=last_pos+1, reason='Theme Update')
                last_pos = cur_role.position

            new_role_map[theme_role] = cur_role
        for role in to_remove:
            await role.delete(reason='Theme Update')

    async def build_theme(self, roles: list[discord.Role]):
        if self.current_theme:
            self.current_theme.current = False
            await self.current_theme.save()
        self.current_theme = Theme(self.server, self.server.name,
                                   [ThemeRole(x.name, str(x.colour), len(x.members)) for x in roles])
        self.current_theme.roles[-1].maximum = -1
        await self.current_theme.save()
        self.current_theme.current = True
        self.current_theme.used = True
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
        members = sorted_members(self.server.members.members.values(), key=lambda x: x.points)
        member_role_pairs = []
        changes: list[tuple['HeliosMember', discord.Role, discord.Role]] = []
        for theme_role in self.current_theme.roles:
            role = self.role_map[theme_role]
            if not role:
                continue
            maximum = theme_role.maximum if theme_role.maximum != -1 else len(members)
            for i in range(maximum):
                member = members.pop()
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
    def __init__(self, server: 'Server', name: str, roles: list['ThemeRole']):
        self.server = server
        self.name = name
        self.roles = roles
        self.current = False
        self.used = False
        self.db_entry: Optional[ThemeModel] = None

    def has_role(self, role: discord.Role):
        return any(role.name == x.name and role.colour == discord.Colour.from_str(x.color) for x in self.roles)

    async def save(self):
        if self.db_entry:
            await self.db_entry.async_update(**self.to_dict())
        else:
            d = self.to_dict()
            self.db_entry = await ThemeModel.create(server=self.server.db_entry, name=d['name'], roles=d['roles'])

    def to_dict(self):
        return {
            'name': self.name,
            'roles': [x.to_dict() for x in self.roles],
            'current': self.current,
            'used': self.used
        }

    @classmethod
    def from_db(cls, server: 'Server', db_entry: ThemeModel):
        theme = cls(server, db_entry.name, [ThemeRole.from_dict(x) for x in db_entry.roles])
        theme.db_entry = db_entry
        theme.current = db_entry.current
        theme.used = db_entry.used
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
            'maximum': self.maximum
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['name'], data['color'], data['maximum'])


class EditThemeView(ui.View):
    def __init__(self, theme: Theme):
        super().__init__()
        self.theme = theme

    @ui.button(label='Edit Name', style=ButtonStyle.primary)
    async def edit_name(self, interaction: Interaction, button: ui.Button):
        pass

    @ui.button(label='Edit Color', style=ButtonStyle.primary)
    async def edit_color(self, interaction: Interaction, button: ui.Button):
        pass

    @ui.button(label='Edit Roles', style=ButtonStyle.primary)
    async def edit_roles(self, interaction: Interaction, button: ui.Button):
        pass
