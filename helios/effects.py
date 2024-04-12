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
import logging
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Union, Optional

import discord
from playhouse.shortcuts import model_to_dict

from .database import EffectModel

if TYPE_CHECKING:
    from .server import Server
    from .dynamic_voice import DynamicVoiceChannel
    from .member import HeliosMember
    from .helios_bot import HeliosBot


logger = logging.getLogger('HeliosLogger.effects')

EffectTarget = Union['HeliosMember', 'DynamicVoiceChannel', 'Server']


class EffectsManager:
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.effects: dict[EffectTarget, list['Effect']] = {}

        self._managing = False

    async def manage_effects(self):
        self._managing = True
        while self._managing:
            try:
                for target, effects in self.effects.items():
                    for effect in effects:
                        if effect.time_left <= 0:
                            await self.remove_effect(effect)
                        else:
                            await effect.enforce()
            except Exception as e:
                logger.error(f'Error in effect manager: {e}', exc_info=True)
            await asyncio.sleep(1)

    def stop_managing(self):
        self._managing = False

    async def fetch_all(self):
        models = await EffectModel.get_all()
        for model in models:
            effect = Effect.from_dict(model_to_dict(model), self.bot)
            if effect is not None:
                effect.db_entry = model
                self._add_effect(effect)

    def _add_effect(self, effect: 'Effect'):
        target = effect.target
        if target not in self.effects:
            self.effects[target] = []
        self.effects[target].append(effect)

    async def add_effect(self, effect: 'Effect'):
        self._add_effect(effect)
        await effect.apply()
        effect.db_entry = await EffectModel.new(**effect.to_dict())

    async def remove_effect(self, effect: 'Effect'):
        target = effect.target
        try:
            self.effects[target].remove(effect)
            await effect.remove()
            if effect.db_entry is not None:
                await effect.db_entry.async_delete()
        except (ValueError, KeyError):
            pass

    def get_effects(self, target: EffectTarget):
        return self.effects.get(target, [])

    async def clear_effects(self, target: EffectTarget):
        effects = self.effects.pop(target, [])
        for effect in effects:
            await effect.remove()


class Effect:
    type = 'Effect'

    def __init__(self, target: EffectTarget, duration: int):
        self.target = target
        self.duration = duration
        self.applied = False
        self.db_entry = None

        self._applied_at: Optional[datetime] = None

    @property
    def time_left(self):
        if self._applied_at is None:
            return self.duration
        return self.duration - (datetime.now().astimezone() - self._applied_at).total_seconds()

    def serialize_target(self) -> Union[str, int]:
        name = type(self.target).__name__
        if name == 'HeliosMember':
            return self.target.json_identifier
        else:
            return self.target.id

    @staticmethod
    def deserialize_target(name: Union[str, int], bot: 'HeliosBot'):
        try:
            name = int(name)
        except ValueError:
            pass
        if isinstance(name, str):
            return bot.get_helios_member(name)
        else:
            server = bot.servers.get(name)
            if server is not None:
                return server
            channel = bot.get_channel(name)
            if channel is not None:
                server = bot.servers.get(channel.guild.id)
                channel = server.channels.dynamic_voice.channels.get(name)
                return channel

    def to_dict(self):
        return {
            'type': self.type,
            'target': self.serialize_target(),
            'duration': self.duration,
            'applied': self.applied,
            'applied_at': self._applied_at,
            'extra': self.to_dict_extras()
        }

    def to_dict_extras(self):
        return {}

    def load_extras(self, data: dict):
        pass

    @classmethod
    def from_dict(cls, data: dict, bot: 'HeliosBot'):
        for subcls in cls.__subclasses__():
            if subcls.type == data['type']:
                return subcls.from_dict(data, bot)
        target = cls.deserialize_target(data['target'], bot)
        if target is None:
            return None
        effect = cls(target, data['duration'])
        effect.applied = data['applied']
        effect._applied_at = data['applied_at']
        effect.load_extras(data['extra'])
        return effect

    async def apply(self):
        self._applied_at = datetime.now().astimezone()
        self.applied = True

    async def enforce(self):
        raise NotImplementedError

    async def remove(self):
        self.applied = False
        self._applied_at = None


class MuteEffect(Effect):
    def __init__(self, target: 'HeliosMember', duration: int, *, cost: int = 0, muter: 'HeliosMember' = None,
                 force: bool = False, reason: str = None, embed: discord.Embed = None):
        super().__init__(target, duration)
        self.cost = cost
        self.muter = muter
        self.force = force
        self.reason = reason
        self.embed = embed

    def to_dict_extras(self):
        return {
            'cost': self.cost,
            'muter': self.muter.id if self.muter else None,
            'force': self.force,
            'reason': self.reason,
            'embed': self.embed.to_dict() if self.embed else None
        }

    def load_extras(self, data: dict):
        self.cost = data.get('cost', self.cost)
        self.muter = self.target.server.members.get(data.get('muter'))
        self.force = data.get('force', self.force)
        self.reason = data.get('reason', self.reason)
        self.embed = discord.Embed.from_dict(data.get('embed')) if data.get('embed') else None

    def get_mute_embed(self):
        if self.embed is not None:
            return self.embed
        embed = discord.Embed(
            title='Muted',
            colour=discord.Colour.orange(),
            description=f'Someone spent **{self.cost}** {self.target.server.points_name.capitalize()} to mute you for '
                        f'**{self.duration}** seconds.'
        )
        return embed

    async def apply(self):
        await super().apply()
        await self.target.voice_mute(reason=self.reason)
        await self.target.member.send(embed=self.get_mute_embed())

    async def remove(self):
        await super().remove()
        await self.target.voice_unmute()

    async def enforce(self):
        voice = self.target.member.voice
        if voice is not None and voice.channel is not None:
            if voice.mute is False:
                await self.target.member.edit(mute=True)


class DeafenEffect(Effect):
    def __init__(self, target: 'HeliosMember', duration: int, *, cost: int = None, deafener: 'HeliosMember' = None,
                 force: bool = False, reason: str = None, embed: discord.Embed = None):
        super().__init__(target, duration)
        self.cost = cost
        self.deafener = deafener
        self.force = force
        self.reason = reason
        self.embed = embed

    def to_dict_extras(self):
        return {
            'cost': self.cost,
            'deafener': self.deafener.id if self.deafener else None,
            'force': self.force,
            'reason': self.reason,
            'embed': self.embed.to_dict() if self.embed else None
        }

    def load_extras(self, data: dict):
        self.cost = data.get('cost', self.cost)
        self.deafener = self.target.server.members.get(data.get('deafener'))
        self.force = data.get('force', self.force)
        self.reason = data.get('reason', self.reason)
        self.embed = discord.Embed.from_dict(data.get('embed')) if data.get('embed') else None

    def get_deafen_embed(self):
        if self.embed is not None:
            return self.embed
        embed = discord.Embed(
            title='Deafened',
            colour=discord.Colour.orange(),
            description=f'Someone spent **{self.cost}** {self.target.server.points_name.capitalize()} to deafen you for '
                        f'**{self.duration}** seconds. **The deafen has just ended.**'
        )
        return embed

    async def apply(self):
        await super().apply()
        await self.target.voice_deafen(reason=self.reason)

    async def remove(self):
        await super().remove()
        await self.target.voice_undeafen()
        await self.target.member.send(embed=self.get_deafen_embed())

    async def enforce(self):
        voice = self.target.member.voice
        if voice is not None and voice.channel is not None:
            if voice.deaf is False:
                await self.target.member.edit(deafen=True)

