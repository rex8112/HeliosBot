from datetime import timedelta

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

        self._current_channel: Optional['DynamicVoiceChannel'] = None
        self._current_target: Optional[HeliosMember] = None
        self._current_sound_file: Optional[str] = None
        self._current_image_file: Optional[str] = None

        self.schedule.add_handler('hint', lambda slot: self.start_hint(slot))
        self.schedule.add_handler('hint_end', lambda slot: self.stop_hint(slot))

    async def schedule_soonest(self, member: 'HeliosMember', sound_file: str, image_file: str) -> None:
        now = utcnow()
        conflict = self.schedule.get_conflicting_slot(now)
        while conflict:
            now = conflict.end
            conflict = self.schedule.get_conflicting_slot(now)
        slot = self.schedule.create_slot(now, now+timedelta(hours=1), 'hint', {})
        if slot:
            self._current_target = member
            self._current_sound_file = sound_file
            self._current_image_file = image_file
        return slot

    async def start_hint(self, slot: 'TimeSlot'):
        channel = await self.voices.get_inactive_channel()
        await channel.make_controlled()
        channel.custom_name = 'Hidden Room'
        await channel.purge_channel()
        await channel.apply_template(self.get_template())
        self._current_channel = channel

    async def stop_hint(self, slot: 'TimeSlot'):
        if self._current_channel:
            await self._current_channel.make_inactive()
            self._current_channel = None
        self._current_sound_file = None
        self._current_image_file = None
        self._current_target = None

    def get_template(self):
        if self._current_target:
            template = VoiceTemplate(self._current_target, 'temp_hint')
            template.private = True
            return template
        return None