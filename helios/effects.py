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
from datetime import datetime
from typing import TYPE_CHECKING, Union, Optional

if TYPE_CHECKING:
    from .server import Server
    from .dynamic_voice import DynamicVoiceChannel
    from .member import HeliosMember
    from .helios_bot import HeliosBot


EffectTarget = Union['HeliosMember', 'DynamicVoiceChannel', 'Server']


class EffectsManager:
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot
        self.effects: dict[EffectTarget, list['Effect']] = {}

    async def add_effect(self, target: EffectTarget, effect: 'Effect'):
        if target not in self.effects:
            self.effects[target] = []
        self.effects[target].append(effect)
        await effect.apply()

    async def remove_effect(self, target: EffectTarget, effect: 'Effect'):
        try:
            self.effects[target].remove(effect)
            await effect.remove()
        except (ValueError, KeyError):
            pass

    def get_effects(self, target: EffectTarget):
        return self.effects.get(target, [])

    async def clear_effects(self, target: EffectTarget):
        effects = self.effects.pop(target, [])
        for effect in effects:
            await effect.remove()


class Effect:
    def __init__(self, target: EffectTarget, duration: int):
        self.target = target
        self.duration = duration
        self.applied = False
        self._applied_at: Optional[datetime] = None

    @property
    def time_left(self):
        if self._applied_at is None:
            return self.duration
        return self.duration - (datetime.now() - self._applied_at).total_seconds()

    async def apply(self):
        self._applied_at = datetime.now()
        self.applied = True

    async def enforce(self):
        raise NotImplementedError

    async def remove(self):
        self.applied = False
        self._applied_at = None


class MuteEffect(Effect):
    def __init__(self, target: 'HeliosMember', duration: int, *, cost: int = None, muter: 'HeliosMember' = None):
        super().__init__(target, duration)
        self.cost = cost
        self.muter = muter

    async def apply(self):
        await super().apply()
        await self.target.voice_mute()

    async def remove(self):
        await super().remove()
        await self.target.voice_unmute()

    async def enforce(self):
        voice = self.target.member.voice
        if voice is not None and voice.channel is not None:
            if voice.mute is False:
                await self.target.member.edit(mute=True)

