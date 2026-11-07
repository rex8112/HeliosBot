from typing import Optional, List

import discord

from discord import ui, SelectOption
from discord.utils import MISSING


class FilteredChannelSelect(ui.Select):
    def __init__(
        self,
        channels: list[discord.TextChannel],
        *,
        custom_id: str = MISSING,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        options: List[SelectOption] = MISSING,
        disabled: bool = False,
        required: bool = True,
        row: Optional[int] = None,
        id: Optional[int] = None,
    ):
        super().__init__(custom_id=custom_id, placeholder=placeholder, min_values=min_values, max_values=max_values, options=options, disabled=disabled, required=required, row=row, id=id)
        self.channels = channels
        self.selected_channels = []
        options = []
        for channel in self.channels:
            options.append(
                discord.SelectOption(
                    label=channel.name,
                    value=str(channel.id)
                )
            )
        self.options = options
