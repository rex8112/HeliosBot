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
from typing import TYPE_CHECKING

import discord

from .tools.settings import Settings, SettingItem

if TYPE_CHECKING:
    from .helios_bot import HeliosBot
    from .server import Server


class VoiceSettings(Settings):
    group = SettingItem('group', None, int)
    owner = SettingItem('owner', None, discord.Member)


class DynamicVoiceChannel:
    channel_type = 'voice_channel'

    def __init__(self, server: 'Server'):
        self.server = server
        self.settings = VoiceSettings(self.bot)

    @property
    def bot(self) -> 'HeliosBot':
        return self.server.bot


class DynamicVoiceGroup:
    def __init__(self, minimum: int, template: str, maximum: int = 0):
        self.min = minimum
        self.max = maximum
        self.template = template

    def get_name(self, number: int):
        return self.template.replace('{n}', str(number))


class VoiceManager:
    def __init__(self):
        ...
