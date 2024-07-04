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
from typing import TYPE_CHECKING, Callable

import discord
from discord import ui, ButtonStyle, Interaction

if TYPE_CHECKING:
    from .server import Server
    from .member import HeliosMember


def sorted_members(members: list['HeliosMember'], key: Callable[['HeliosMember'], int]) -> list['HeliosMember']:
    s_members = sorted(members, key=lambda x: key(x))
    return list(s_members)


class ThemeManager:
    def __init__(self, server: 'Server'):
        self.server = server
        self.current_theme = None
        self.role_map: dict['ThemeRole', discord.Role] = {}

    def build_role_map(self):
        self.role_map = {}
        for t_role in self.current_theme.roles:
            d_role = discord.utils.get(self.server.guild.roles, name=t_role.name,
                                       colour=discord.Colour.from_str(t_role.color))
            self.role_map[t_role] = d_role

    async def sort_members(self):
        if not self.current_theme:
            return
        members = sorted_members(self.server.members, key=lambda x: x.points)
        member_role_pairs = []
        for theme_role in self.current_theme.roles:
            role = self.role_map[theme_role]
            if not role:
                continue
            for i in range(theme_role.maximum):
                member = members.pop()
                member_role_pairs.append((member, role))
        for member, role in member_role_pairs:
            has_correct_roles = True
            for theme_role in self.current_theme.roles:
                d_role = self.role_map[theme_role]
                if d_role == role:
                    if d_role not in member.member.roles:
                        has_correct_roles = False
                        break
                else:
                    if d_role in member.member.roles:
                        has_correct_roles = False
                        break
            if not has_correct_roles:
                try:
                    await member.member.add_roles(role, reason='Theme Sort')
                    await member.member.remove_roles(*[x for x in self.role_map.values() if x != role],
                                                     reason='Theme Sort')
                except (discord.Forbidden, discord.HTTPException):
                    pass


class Theme:
    def __init__(self, name: str, roles: list['ThemeRole']):
        self.name = name
        self.roles = roles

    def has_role(self, role: discord.Role):
        return any(role.name == x.name and role.colour == discord.Colour.from_str(x.color) for x in self.roles)


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
