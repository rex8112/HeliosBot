from datetime import datetime

import discord
from discord.utils import utcnow

from ..tools.settings import Settings, SettingItem, StringSettingItem


class VoiceSettings(Settings):
    number = SettingItem('number', 0, int)
    group = SettingItem('group', None, int)
    state = SettingItem('state', 1, int)
    owner = SettingItem('owner', None, discord.Member)
    template = StringSettingItem('template', None)
    control_message = SettingItem('control_message', None, discord.PartialMessage)
    inactive = SettingItem('inactive', False, bool)
    custom_name = SettingItem('custom_name', None, str)
    inactive_on = SettingItem('inactive_on', utcnow(), datetime)


class DynamicVoiceGroupSettings(Settings):
    min = SettingItem('min', 1, int)
    min_empty = SettingItem('min_empty', 1, int)
    max = SettingItem('max', 0, int)
    template = StringSettingItem('template', 'Channel {n}', min_length=3, max_length=25)
    game_template = StringSettingItem('game_template', 'Channel {n} - {g}', min_length=3, max_length=22)
