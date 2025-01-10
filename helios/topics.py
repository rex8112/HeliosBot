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
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

import discord

from .enums import TopicChannelStates
from .database import TopicModel, TopicSubscriptionModel

if TYPE_CHECKING:
    from .member import HeliosMember
    from .server import Server


def _get_archive_time():
    return datetime.now().astimezone() + timedelta(hours=24)


class TopicChannel:
    def __init__(self, server: 'Server', channel: discord.TextChannel):
        self.server = server
        self.channel = channel

        self.points: int = 0
        self.authors: list[int] = []
        self.state: TopicChannelStates = TopicChannelStates.Active
        self.creator: Optional['HeliosMember'] = None
        self.archive_message: Optional[discord.Message] = None
        self.archive_date: Optional[datetime] = None

        self.last_solo_message: Optional[datetime] = None

        self.db_entry: Optional['TopicModel'] = None

    @property
    def id(self):
        return self.channel.id

    @property
    def archive_category(self) -> Optional[discord.CategoryChannel]:
        return self.server.settings.archive_category.value

    @property
    def topic_category(self) -> Optional[discord.CategoryChannel]:
        return self.server.settings.topic_category.value

    @property
    def bot(self):
        return self.server.bot

    @property
    def oldest_allowed(self) -> datetime:
        """
        Get the datetime of how old the last message has to be for the channel to get marked
        :return: An aware datetime that is in local time
        """
        delta = timedelta(days=1)
        now = datetime.now().astimezone()
        return now - delta

    @property
    def alive(self):
        if self.channel is not None and self.bot.get_channel(self.id):
            return True
        else:
            return False

    @property
    def active(self):
        return self.state == TopicChannelStates.Active or self.pinned

    @property
    def active_only(self):
        return self.state == TopicChannelStates.Active

    @property
    def pending(self):
        return self.state == TopicChannelStates.PendingArchive

    @property
    def pinned(self):
        return self.state == TopicChannelStates.Pinned

    @property
    def solo_author_id(self) -> Optional[int]:
        tmp = self.authors.copy()
        try:
            tmp.remove(self.bot.user.id)
        except ValueError:
            ...
        if len(tmp) == 1:
            return tmp[0]
        return None

    @property
    def role_name(self):
        if self.channel is None:
            return '_sub'
        return f'{self.channel.name}_sub'

    def serialize(self):
        return {
            'channel_id': self.channel.id,
            'points': self.points,
            'state': self.state.value,
            'creator': self.creator.db_entry if self.creator else None,
            'archive_message': self.archive_message.id if self.archive_message else None,
            'archive_date': self.archive_date
        }

    async def save(self):
        if self.db_entry is None:
            self.db_entry = await TopicModel.async_create(self.channel.id, self.server.db_entry,
                                                          self.creator.db_entry if self.creator else None, self.points,
                                                          self.state.value)
        else:
            data = self.serialize()
            del data['channel_id']
            del data['creator']
            TopicModel.update_model_instance(self.db_entry, data)
            await self.db_entry.async_save()

    # noinspection PyUnresolvedReferences
    @classmethod
    async def load(cls, server: 'Server', db_entry: TopicModel):
        channel = server.guild.get_channel(db_entry.channel_id)
        self = cls(server, channel)
        self.db_entry = db_entry
        self.points = db_entry.points
        self.state = TopicChannelStates(db_entry.state)
        self.creator = await server.members.fetch(db_entry.creator_id) if db_entry.creator_id else None
        try:
            self.archive_message = (await channel.fetch_message(db_entry.archive_message)
                                    if db_entry.archive_message else None)
        except discord.NotFound:
            self.archive_message = None
        self.archive_date = db_entry.archive_date
        return self

    @classmethod
    async def get_all(cls, server: 'Server'):
        entries = await TopicModel.get_all(server.db_entry)
        return [await cls.load(server, entry) for entry in entries]

    async def delete(self, del_channel=True):
        try:
            if del_channel:
                await self.channel.delete()
            role = self.get_role()
            if role:
                await role.delete()
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            pass
        finally:
            await self.db_entry.async_delete()

    async def get_last_week_authors_value(self) -> dict[int, int]:
        week_ago = datetime.now() - timedelta(days=7)
        authors = {}
        async for msg in self.channel.history(after=week_ago):
            author = msg.author
            if not author.bot:
                authors[author.id] = 0.05 + authors.get(author.id, 1.95)
        return authors

    async def get_points(self) -> int:
        authors = await self.get_last_week_authors_value()
        self.points = sum(authors.values())
        self.authors = list(authors.keys())
        return self.points

    async def mark(self, post=True) -> None:
        """
        Set whether the channel is marked for archival.
        :param post: Whether to make/edit a post about it
        """
        self.state = TopicChannelStates.PendingArchive
        self.archive_date = _get_archive_time()
        if post:
            await self.post_archive_message(embed=self._get_marked_embed())
        await self.channel.edit(name=f'🛑{self.channel.name}')

    async def archive(self) -> None:
        if self.archive_category is None:
            return
        self.state = TopicChannelStates.Archived
        await self.channel.edit(category=self.archive_category, sync_permissions=True)
        await self.delete_role()
        if self.archive_message is None:
            await self.post_archive_message(embed=self._get_marked_embed())
        else:
            await self.archive_message.edit(embed=self._get_marked_embed())

    async def post_archive_message(self, content=None, *, embed=None, view=None):
        message = self.archive_message
        if type(message) is discord.PartialMessage:
            message = await message.fetch()
        if message is not None:
            await message.delete()
        new_message = await self.channel.send(content=content, embed=embed,
                                              view=view)
        self.archive_message = new_message

    async def restore(self, saver: 'HeliosMember', delete=True, *, ping_role=False, ping_message: discord.Message = None) -> None:
        self.last_solo_message = None
        embed = self._get_saved_embed()
        old_state = self.state
        self.state = TopicChannelStates.Active
        self.archive_date = None
        await self.channel.edit(name=self.channel.name.replace('🛑', ''),
                                category=self.topic_category,
                                sync_permissions=True)
        embed.set_author(name=saver.member.display_name, icon_url=saver.member.display_avatar.url)
        if self.archive_message is not None:
            await self.archive_message.edit(embed=embed, view=None, delete_after=15 if delete else None)
            self.archive_message = None
        role = self.get_role()
        if role:
            return
        embed = discord.Embed(
            colour=discord.Colour.green(),
            title='Rebuilding Role',
            description='Rebuilding role for topic...'
        )
        message = await self.channel.send(embed=embed)
        async with message.channel.typing():
            await self.create_role()
            await message.delete()
        if ping_role:
            await self.channel.send(f'{role.mention}', reference=ping_message)

    async def pin(self, pinner: 'HeliosMember') -> None:
        if self.state == TopicChannelStates.Pinned:
            self.state = TopicChannelStates.Active
            return
        if not self.active:
            await self.restore(pinner)
        self.state = TopicChannelStates.Pinned

    async def get_markable(self) -> bool:
        """
        Returns whether the channel is eligible to be marked for archival
        """
        messages = [message async for message in self.channel.history(limit=1)]
        if len(messages) > 0:
            last_message = messages[0]
        else:
            last_message = None
        if last_message is None:
            time = self.channel.created_at
        else:
            time = last_message.created_at
        return time < self.oldest_allowed

    async def subscribe(self, member: 'HeliosMember'):
        existing = await TopicSubscriptionModel.get(member.db_entry, self.db_entry)
        if not existing:
            await TopicSubscriptionModel.create(member.db_entry, self.db_entry)
        role = self.get_role()
        if role:
            await member.member.add_roles(role, reason='Subscribed to topic')

    async def unsubscribe(self, member: 'HeliosMember'):
        existing = await TopicSubscriptionModel.get(member.db_entry, self.db_entry)
        if existing:
            await existing.async_delete()
        role = self.get_role()
        if role:
            await member.member.remove_roles(role, reason='Unsubscribed from topic')

    async def get_subscribers(self):
        entries = await TopicSubscriptionModel.get_all_by_topic(self.db_entry)
        return [await self.server.members.fetch(entry.member.member_id) for entry in entries]

    async def create_role(self):
        role = await self.channel.guild.create_role(name=self.role_name, mentionable=True)
        for member in await self.get_subscribers():
            await member.member.add_roles(role, reason='Role created for topic')
        return role

    def get_role(self):
        return discord.utils.get(self.server.guild.roles, name=self.role_name)

    async def delete_role(self):
        role = self.get_role()
        if role:
            await role.delete()

    def get_archivable(self) -> bool:
        """
        Returns whether the channel is ready to be archived
        """
        now = datetime.now().astimezone()
        marked = self.state == TopicChannelStates.PendingArchive
        default = now + timedelta(days=1)
        archive_at = self.archive_date
        if archive_at is None:
            archive_at = default
        timing = archive_at < now
        return marked and timing

    async def evaluate_state(self):
        if self.state == TopicChannelStates.PendingArchive:
            if self.get_archivable():
                await self.archive()
        elif self.state == TopicChannelStates.Active:
            if await self.get_markable():
                await self.mark()

    def get_description(self, new_name: str = None) -> str:
        return (f'Discussions about the topic "{new_name if new_name else self.channel.name}". If you would like to '
                f'subscribe to this topic, '
                'run the command `/topic subscribe` in this channel. If you would like to mention all subscribers, '
                'while the topic is archived, simply include a @Helios in your message and the bot will mention the '
                'role when it is restored.')

    def _get_marked_embed(self) -> discord.Embed:
        t = self.archive_date
        word = 'archived'
        embed = discord.Embed(
            colour=discord.Colour.red(),
            title=f'⚠ Flagged to be {word.capitalize()} ⚠',
            description=(
                f'This channel has been flagged due to inactivity. The channel will be {word} '
                f'<t:{int(t.timestamp())}:R> for later retrieval.'
            )
        )
        embed.add_field(
            name=f'{word.capitalize()[:-1]} Time',
            value=f'<t:{int(t.timestamp())}:f>'
        )
        return embed

    def _get_saved_embed(self) -> discord.Embed:
        word = 'Archive'
        if self.state == TopicChannelStates.Archived:
            embed = discord.Embed(
                colour=discord.Colour.green(),
                title='Channel Restored',
                description=f'Channel restored.'
            )
        else:
            embed = discord.Embed(
                colour=discord.Colour.green(),
                title=f'{word} Aborted',
                description=f'{word} was successfully aborted.'
            )
        return embed
