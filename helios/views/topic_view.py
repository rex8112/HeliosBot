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

from typing import Optional, TYPE_CHECKING, Iterable, Self, Any, List

import discord

from discord import ui, Interaction
from discord.utils import format_dt, MISSING
from .components.generic_selects import FilteredChannelSelect

__all__ = ('TopicSubView',)


if TYPE_CHECKING:
    from ..topics import TopicChannel
    from ..server import Server
    from ..member import HeliosMember


class FilteredChannelsModal(ui.Modal):
    def __init__(
            self,
            channels: List[discord.TextChannel],
            *,
            title: str = MISSING,
            timeout: Optional[float] = None,
    ):
        super().__init__(title=title, timeout=timeout)
        self.select = FilteredChannelSelect(channels)
        self.add_item(ui.Label(text=title, component=self.select))


        self.selected_channels = []

    async def on_submit(self, interaction: Interaction, /) -> None:
        str_ids = self.select.values
        channels = [interaction.guild.get_channel(int(i)) for i in str_ids]
        self.selected_channels = channels
        await interaction.response.send_message(content=f'Send a message in {channels[0].mention} and I will unarchive it. '
                                                        f'If you {interaction.guild.me.mention} I will ping the subscription role once I rebuild it.',
                                                ephemeral=True)


class TopicSubButton(ui.Button['TopicSubView']):
    def __init__(self, topic: 'TopicChannel'):
        super().__init__(label='Subscribe', custom_id=f'{topic.id}')
        self.topic = topic

    async def callback(self, interaction: Interaction) -> Any:
        member = self.topic.server.members.get(interaction.user.id)
        if member:
            if await self.topic.is_subscribed(member):
                await interaction.response.send_message(f'You are already subscribed to {self.topic.channel.name}!',
                                                        ephemeral=True)
            else:
                await self.topic.subscribe(member)
                await interaction.response.send_message(f'You have **subscribed** to {self.topic.channel.name}!',
                                                        ephemeral=True)


class TopicActionRow(ui.ActionRow['TopicSubView']):
    @ui.button(label='New', style=discord.ButtonStyle.green)
    async def new_topic(self, interaction: discord.Interaction, button: discord.Button):
        pass

    @ui.button(label='Unarchive', style=discord.ButtonStyle.blurple)
    async def unarchive(self, interaction: discord.Interaction, button: discord.Button):
        archived: list['TopicChannel'] = list(filter(lambda x: not x.active, self.view.server.channels.topic_channels.values()))
        modal = FilteredChannelsModal([t.channel for t in archived], title='Select Channel to Unarchive', timeout=60)
        await interaction.response.send_modal(modal)

    @ui.button(label='Subs')
    async def subs(self, interaction: discord.Interaction, button: discord.Button):
        pass

    @ui.button(label='Help', disabled=True)
    async def help(self, interaction: discord.Interaction, button: discord.Button):
        pass


class TopicSubView(ui.LayoutView):
    container = ui.Container()

    def __init__(self, server: 'Server', topics: Iterable['TopicChannel'], first=True) -> None:
        super().__init__(timeout=None)
        self.server = server
        self.topics = topics
        self.first = first

    async def setup(self) -> Self:
        for topic in self.topics:
            text = f'{topic.channel.name}'
            if topic.archive_date:
                text += f'\n-# Archive {format_dt(topic.archive_date, style="R")}'
            self.container.add_item(ui.Section(
                ui.TextDisplay['TopicSubView'](text),
                accessory=TopicSubButton(topic)
            ))

        #self.container.add_item(ui.Separator())

        #self.container.add_item(TopicActionRow())
        return self


class TopicView(ui.LayoutView):
    container = ui.Container()

    def __init__(self, server: 'Server', topics: Iterable['TopicChannel']) -> None:
        super().__init__(timeout=None)
        self.server = server
        self.topics = topics

    async def setup(self) -> Self:
        self.container.add_item(ui.TextDisplay(
            f'## {self.server.guild.name} Topic Channels'
        ))

        self.container.add_item(TopicActionRow())
        return self
