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

from typing import Union, TYPE_CHECKING

import discord

from .exceptions import IdMismatchError

if TYPE_CHECKING:
    from .member import HeliosMember
    from .helios_bot import HeliosBot


class VoiceTemplate:
    _deny_permissions = discord.PermissionOverwrite(
        view_channel=False,
        connect=False,
        send_messages=False,
        read_messages=False
    )
    _allow_permissions = discord.PermissionOverwrite(
        view_channel=True,
        connect=True,
        send_messages=True,
        read_messages=True
    )

    def __init__(self, owner: 'HeliosMember', name: str, *, data: dict = None):
        self.id = 0
        self.owner = owner
        self.guild = owner.guild
        self.name = name

        self.nsfw: bool = False
        self.private: bool = True
        self.allowed: dict[int, discord.Member] = {}
        self.denied: dict[int, discord.Member] = {}
        if data:
            self._deserialize(data)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, VoiceTemplate):
            return self.serialize() == o.serialize()

    @property
    def permissions(self) -> list[tuple[Union[discord.Role, discord.Member],
                                        discord.PermissionOverwrite]]:
        """
        A list of (target, permission) tuple pairs.
        """
        permissions = []

        if self.private:
            permissions.append((self.guild.default_role,
                                self._deny_permissions))
        else:
            role = self.owner.server.verified_role if self.owner.server.verified_role else self.guild.default_role
            permissions.append((role, self._allow_permissions))

        for member in self.allowed.values():
            permissions.append((member, self._allow_permissions))

        for member in self.denied.values():
            permissions.append((member, self._deny_permissions))

        permissions.append((self.guild.me, self._allow_permissions))
        permissions.append((self.owner.member, self._allow_permissions))

        return permissions

    @property
    def overwrites(self):
        overwrites = {}
        for key, perm in self.permissions:
            overwrites[key] = perm
        return overwrites

    @property
    def bot(self) -> 'HeliosBot':
        return self.owner.bot

    def allow(self, member: discord.Member) -> tuple[discord.Member, discord.PermissionOverwrite]:
        self.allowed[member.id] = member
        if member.id in self.denied:
            del self.denied[member.id]

        return member, self._allow_permissions

    def deny(self, member: discord.Member) -> tuple[discord.Member, discord.PermissionOverwrite]:
        self.denied[member.id] = member
        if member.id in self.allowed:
            del self.allowed[member.id]

        return member, self._deny_permissions

    def clear(self, member: discord.Member) -> tuple[discord.Member, None]:
        if member.id in self.denied:
            del self.denied[member.id]
        if member.id in self.allowed:
            del self.allowed[member.id]

        return member, None

    def _deserialize(self, data: dict) -> None:
        if data.get('owner') != self.owner.member.id or data.get('guild') != self.guild.id:
            raise IdMismatchError('Guild or Owner Id does not match')
        self.id = data.get('id')
        self.name = data.get('name')
        self.private = data.get('private')
        self.nsfw = data.get('nsfw')
        allowed = [(x, self.guild.get_member(x)) for x in data.get('allowed')]
        denied = [(x, self.guild.get_member(x)) for x in data.get('denied')]
        for key, value in allowed:
            if value is None:
                continue
            self.allowed[key] = value
        for key, value in denied:
            if value is None:
                continue
            self.denied[key] = value

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'owner': self.owner.member.id,
            'guild': self.guild.id,
            'private': self.private,
            'nsfw': self.nsfw,
            'allowed': list(self.allowed.keys()),
            'denied': list(self.denied.keys())
        }

    def is_stored(self):
        return self in self.owner.templates

    async def save(self):
        await self.owner.save(force=True)
