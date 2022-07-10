from typing import Union

import discord

from .exceptions import IdMismatchError


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

    def __init__(self, owner: discord.Member, name: str):
        self.id = 0
        self.owner = owner
        self.guild = owner.guild
        self.name = name

        self.nsfw: bool = False
        self.private: bool = True
        self.allowed: dict[int, discord.Member] = {}
        self.denied: dict[int, discord.Member] = {}

    @property
    def permissions(self) -> list[tuple[Union[discord.Role, discord.Member], discord.PermissionOverwrite]]:
        """
        A list of (target, permission) tuple pairs.
        """
        permissions = [(self.guild.me, self._allow_permissions)]

        if self.private:
            permissions.append((self.guild.default_role, self._deny_permissions))
        else:
            permissions.append((self.guild.default_role, self._allow_permissions))

        for member in self.allowed.values():
            permissions.append((member, self._allow_permissions))

        for member in self.denied.values():
            permissions.append((member, self._deny_permissions))

        return permissions

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

    def deserialize(self, data: dict) -> None:
        if data.get('owner') != self.owner.id or data.get('guild') != self.guild.id:
            raise IdMismatchError('Guild or Owner Id does not match')
        self.id = data.get('id')
        self.name = data.get('name')
        self.private = data.get('private')
        self.nsfw = data.get('nsfw')
        allowed = [(x, self.guild.get_member(x)) for x in data.get('allowed')]
        denied = [(x, self.guild.get_member(x)) for x in data.get('denied')]
        for key, value in allowed:
            self.allowed[key] = value
        for key, value in denied:
            self.denied[key] = value

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'owner': self.owner.id,
            'guild': self.guild.id,
            'private': self.private,
            'nsfw': self.nsfw,
            'allowed': list(self.allowed.keys()),
            'denied': list(self.denied.keys())
        }
