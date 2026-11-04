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

from typing import Optional, TYPE_CHECKING, Iterable, Self, Any

import discord

from discord import ui, Interaction

__all__ = ('TopicSubView',)

from discord.utils import format_dt

if TYPE_CHECKING:
    from ..topics import TopicChannel
    from ..server import Server


class TopicSubButton(ui.Button['TopicSubView']):
    def __init__(self, topic: 'TopicChannel'):
        super().__init__(label='Subscribe', custom_id=f'{topic.id}')
        self.topic = topic

    async def callback(self, interaction: Interaction) -> Any:
        member = self.topic.server.members.get(interaction.user.id)
        if member:
            if await self.topic.is_subscribed(member):
                await self.topic.unsubscribe(member)
                await interaction.response.send_message(f'You have **unsubscribed** from {self.topic.channel.name}!',
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
        pass

    @ui.button(label='Subs')
    async def subs(self, interaction: discord.Interaction, button: discord.Button):
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
