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
from discord._types import ClientT
from discord.utils import format_dt, MISSING

from .components.generic_selects import FilteredChannelSelect
from ..colour import Colour

__all__ = ('TopicSubView',)


if TYPE_CHECKING:
    from ..topics import TopicChannel
    from ..server import Server
    from ..member import HeliosMember


class NewTopicModal(ui.Modal):
    name = ui.Label(text='Name of the new channel',
                    component=ui.TextInput(min_length=3, max_length=25))
    confirm = ui.Label(text='Confirm', component=ui.CheckboxGroup(min_values=1))

    def __init__(self, server: 'Server'):
        super().__init__(timeout=120, title='New Topic Channel')
        self.server = server
        self.last_interaction: Optional[discord.Interaction] = None

        self.confirm.component.options = [
            discord.CheckboxGroupOption(label='I confirm I have looked through the channels to ensure there is not a duplicate.')
        ]

    async def on_submit(self, interaction: Interaction, /) -> None:
        if self.confirm.component.values:
            await interaction.response.defer(ephemeral=True, thinking=True)
            name = self.name.component.value
            member = self.server.members.get(interaction.user.id)
            res, msg = await self.server.channels.create_topic(name, member)
            await interaction.followup.send(content=msg)
        else:
            await interaction.response.send_message('Did not confirm', ephemeral=True)


class FilteredChannelsModal(ui.Modal):
    def __init__(
            self,
            channels: List[discord.TextChannel],
            *,
            title: str = MISSING,
            timeout: Optional[float] = None,
            max_select = 1
    ):
        max_select = min(max_select, len(channels))
        super().__init__(title=title, timeout=timeout)
        self.select = FilteredChannelSelect(channels[:25], max_values=max_select)
        self.select2 = None
        self.add_item(ui.Label(text=title, component=self.select))

        if len(channels) > 25:
            self.select2 = FilteredChannelSelect(channels[25:], max_values=max_select)
            self.add_item(ui.Label(text=title, component=self.select2))


        self.selected_channels = []
        self.last_interaction: Optional[discord.Interaction] = None

    def get_selected(self) -> list[str]:
        str_ids = self.select.values
        if self.select2:
            str_ids += self.select2.values
        return str_ids

    async def on_submit(self, interaction: Interaction, /) -> None:
        str_ids = self.get_selected()
        channels = [interaction.guild.get_channel(int(i)) for i in str_ids]
        self.selected_channels = channels
        self.last_interaction = interaction


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


class TopicUnsubButton(ui.Button):
    def __init__(self, server: 'Server', channels: list['TopicChannel']):
        super().__init__(style=discord.ButtonStyle.green, label='Unsubscribe')
        self.server = server
        self.channels = channels

    async def callback(self, interaction: Interaction) -> Any:
        modal = FilteredChannelsModal([x.channel for x in self.channels],
                                      title='Select Channels to Unsubscribe From',
                                      max_select=50)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return

        interaction = modal.last_interaction
        if interaction is None:
            return

        if modal.selected_channels:
            await interaction.response.defer(ephemeral=True, thinking=True)
            unsub_txt = ''
            for channel in self.channels:
                if channel.channel in modal.selected_channels:
                    await channel.unsubscribe(self.server.members.get(interaction.user.id))
                    unsub_txt += f'{channel.channel.mention} '
            await interaction.followup.send(content=f'### Unsubscribed From\n{unsub_txt}', ephemeral=True)
        else:
            await interaction.response.send_message(content=f'Nothing Selected', ephemeral=True)


class TopicActionRow(ui.ActionRow['TopicSubView']):
    @ui.button(label='New', style=discord.ButtonStyle.green)
    async def new_topic(self, interaction: discord.Interaction, button: discord.Button):
        server: 'Server' = self.view.server
        await interaction.response.send_modal(NewTopicModal(server))

    @ui.button(label='Unarchive', style=discord.ButtonStyle.blurple)
    async def unarchive(self, interaction: discord.Interaction, button: discord.Button):
        archived: list['TopicChannel'] = list(filter(lambda x: not x.active, self.view.server.channels.topic_channels.values()))
        if len(archived) == 0:
            await interaction.response.send_message(content='Nothing to unarchive', ephemeral=True)
            return

        modal = FilteredChannelsModal([t.channel for t in archived], title='Select Channel to Unarchive', timeout=60)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.last_interaction
        if interaction:
            await interaction.response.send_message(content=f'Send a message in {modal.selected_channels[0].mention} '
                                                            f'and I will unarchive it. If you put '
                                                            f'{interaction.guild.me.mention} in the message I will ping the '
                                                            f'subscription role once I rebuild it.',
                                                    ephemeral=True)

    @ui.button(label='Subs')
    async def subs(self, interaction: discord.Interaction, button: discord.Button):
        server: 'Server' = self.view.server
        member = server.members.get(interaction.user.id)
        if member is None:
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        subbed = await server.channels.get_subs(member)

        container = ui.Container(accent_color=Colour.helios())
        container.add_item(
            ui.TextDisplay(
                f'## Currently Subbed\n'
                f'{"\n".join(x.channel.mention for x in subbed)}'
            )
        )
        container.add_item(
            ui.ActionRow(
                TopicUnsubButton(server, subbed)
            )
        )
        view = ui.LayoutView()
        view.add_item(container)

        await interaction.followup.send(view=view)


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
