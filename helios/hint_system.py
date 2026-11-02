import asyncio
from datetime import timedelta

import discord
from discord.utils import utcnow
from typing import TYPE_CHECKING, Optional

from .voice_template import VoiceTemplate

if TYPE_CHECKING:
    from .dynamic_voice import DynamicVoiceChannel
    from .voice_scheduler import TimeSlot
    from .member import HeliosMember
    from .helios_voice_controller import HeliosVoiceController


class HintSystem:
    def __init__(self, vc: 'HeliosVoiceController'):
        self.vc = vc
        self.server = self.vc.server
        self.voices = self.server.channels.dynamic_voice
        self.schedule = self.vc.schedule

        self._slot: Optional['TimeSlot'] = None
        self._current_channel: Optional['DynamicVoiceChannel'] = None
        self._current_target: Optional[HeliosMember] = None
        self._current_sound_file: Optional[str] = None
        self._current_image_file: Optional[str] = None
        self._stopping = False
        self._task: Optional[asyncio.Task] = None

        self.schedule.add_handler('hint', lambda slot: self.start_hint(slot))
        self.schedule.add_handler('hint_end', lambda slot: self.stop_hint(slot))

    async def schedule_soonest(self, member: 'HeliosMember', sound_file: str, image_file: str) -> None:
        now = utcnow()
        conflict = self.schedule.get_conflicting_slot(now)
        while conflict:
            now = conflict.end
            conflict = self.schedule.get_conflicting_slot(now)
        slot = self.schedule.create_slot(now, now+timedelta(minutes=15), 'hint', {})
        if slot:
            self._current_target = member
            self._current_sound_file = sound_file
            self._current_image_file = image_file
        return slot

    async def start_hint(self, slot: 'TimeSlot'):
        self._stopping = False
        self._slot = slot
        channel = await self.voices.get_inactive_channel()
        await channel.make_controlled(None)
        channel.custom_name = 'Hidden Room'
        await channel.purge_channel()
        await channel.apply_template(self.get_template())
        self._current_channel = channel
        self._task = asyncio.create_task(self.run())

    async def stop_hint(self, slot: 'TimeSlot'):
        self._stopping = True
        self._slot = None
        if self._current_channel:
            await self._current_channel.make_inactive()
            self._current_channel = None
        self._current_sound_file = None
        self._current_image_file = None
        self._current_target = None
        self._task = None

    async def run(self):
        await self.vc.connect(self._current_channel.channel)
        try:
            while not self._stopping:
                if self._current_target.member in self._current_channel.channel.members:
                    file = discord.File(self._current_image_file)
                    source = discord.FFmpegPCMAudio(self._current_sound_file)
                    await self.vc.play(source)
                    await self._current_target.member.send(file=file)
                    self._stopping = True
                else:
                    await asyncio.sleep(5)
        except Exception as e:
            pass
        finally:
            await self.vc.disconnect()
            self._slot.end = utcnow()

    def get_template(self):
        if self._current_target:
            template = VoiceTemplate(self._current_target, 'temp_hint')
            template.private = True
            return template
        return None