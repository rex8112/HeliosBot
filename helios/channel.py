import datetime
import json
from typing import TYPE_CHECKING, Optional, Union

import discord

from .views import TopicView

if TYPE_CHECKING:
    from helios import ChannelManager, HeliosBot
    from .voice_template import VoiceTemplate


class Channel:
    channel_type = 'basic'
    _default_settings = {}
    _allowed_flags = []

    def __init__(self,
                 manager: 'ChannelManager',
                 data: dict):
        """
        A special channel class that will hold all the important functions of that class
        :param manager: The channel manager handling this channel
        :param data: Channel data dict
        """
        self.bot: 'HeliosBot' = manager.bot
        self.manager = manager
        self.channel = None
        self.settings = self._default_settings.copy()
        self.flags = []
        self._id = None

        self._id = data['id']
        self.channel = self.bot.get_channel(self._id)
        self._new = False

        self._deserialize(data)

    @property
    def id(self):
        if self.channel:
            return self.channel.id
        else:
            return self._id

    @property
    def server(self):
        return self.manager.server

    @property
    def alive(self):
        if self.bot.get_channel(self.id):
            return True
        else:
            return False

    @classmethod
    def new(cls, manager: 'ChannelManager', channel_id: int):
        data = {
            'id': channel_id,
            'type': cls.channel_type,
        }
        c = cls(manager, data)
        c._new = True
        return c

    async def save(self):
        if self._new:
            await self.bot.helios_http.post_channel(self.serialize())
            self._new = False
        else:
            await self.bot.helios_http.patch_channel(self.serialize())

    async def delete(self, del_channel=True):
        try:
            if del_channel:
                await self.channel.delete()
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            pass
        finally:
            await self.bot.helios_http.del_channel(self.id)

    def set_flag(self, flag: str, on: bool):
        if flag not in self._allowed_flags:
            raise KeyError(f'{flag} not in {type(self)} allowed flags: {self._allowed_flags}')
        if flag in self.flags and on is False:
            self.flags.remove(flag)
        elif flag not in self.flags and on is True:
            self.flags.append(flag)

    def get_flag(self, flag: str):
        return flag in self.flags

    def _deserialize(self, data: dict) -> None:
        if self.channel_type != data.get('type'):
            raise TypeError(f'Channel data is of type `{data.get("type")}` not `{self.channel_type}`')
        self.flags = data.get('flags', self.flags)
        settings = data.get('settings', {})
        for k, v in settings.items():
            self.settings[k] = v

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'server': self.server.id,
            'type': self.channel_type,
            'settings': self.settings,
            'flags': self.flags
        }


def _get_archive_time():
    return datetime.datetime.now().astimezone() + datetime.timedelta(hours=30)


class TopicChannel(Channel):
    channel_type = 'topic'
    _default_settings = {
        'tier': 1,
        'saves_in_row': 0,
        'creator': None,
        'archive_at': None,
        'archive_message_id': None,
    }
    _allowed_flags = [
        'MARKED',
        'ARCHIVED',
    ]
    _repeated_authors_value = 1 / 20  # Users per messages
    _tier_thresholds_lengths = {
        0: datetime.timedelta(days=1),
        2: datetime.timedelta(days=3),
        5: datetime.timedelta(days=7),
        10: datetime.timedelta(days=14),
        20: datetime.timedelta(days=28)
    }

    def __init__(self, manager: 'ChannelManager', data: dict):
        super().__init__(manager, data)

    @property
    def oldest_allowed(self) -> datetime.datetime:
        """
        Get the datetime of how old the last message has to be for the channel to get marked
        :return: An aware datetime that is in local time
        """
        delta = list(self._tier_thresholds_lengths.values())[self.settings.get('tier') - 1]
        now = datetime.datetime.now().astimezone()
        return now - delta

    @property
    def archive_time(self) -> Optional[datetime.datetime]:
        raw_time = self.settings.get('archive_at')
        if raw_time:
            return datetime.datetime.fromisoformat(raw_time)
        return None

    @property
    def archive_category(self) -> Optional[discord.CategoryChannel]:
        channel_id = self.server.settings.get('archive_category')
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

    @property
    def topic_category(self) -> Optional[discord.CategoryChannel]:
        channel_id = self.server.settings.get('topic_category')
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

    def tier_duration(self, tier: int) -> datetime.timedelta:
        return list(self._tier_thresholds_lengths.values())[tier - 1]

    async def _get_last_week_authors_value(self) -> dict[int, int]:
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        authors = {}
        async for msg in self.channel.history(after=week_ago):
            author = msg.author
            if not author.bot:
                authors[author.id] = 0.05 + authors.get(author.id, 0.95)
        return authors

    async def set_marked(self, state: bool, post=True) -> None:
        """
        Set whether the channel is marked for archival.
        :param state: The state to set it to
        :param post: Whether to make/edit a post about it
        """
        self.set_flag('MARKED', state)
        if state:
            self.settings['archive_at'] = _get_archive_time().isoformat()
        else:
            self.settings['archive_at'] = None
        if post:
            if state:
                await self.post_archive_message(embed=self._get_marked_embed(), view=TopicView(self.bot))
            else:
                await self.post_archive_message(embed=self._get_saved_embed())

    async def set_archive(self, state: bool, post=True) -> None:
        self.set_flag('ARCHIVED', state)
        self.settings['archive_at'] = None
        if state:
            await self.set_marked(False, post=False)
            await self.channel.edit(category=self.archive_category)
        else:
            await self.channel.edit(category=self.topic_category)

    async def save_channel(self, interaction: discord.Interaction = None):
        post = interaction is None
        if self.get_flag('ARCHIVED'):
            await self.set_archive(False, post=post)
        elif self.get_flag('MARKED'):
            await self.set_marked(False, post=post)
        if not post:
            await interaction.response.edit_message(embed=self._get_saved_embed(), view=None)
        self.settings['archive_message_id'] = None

    async def evaluate_tier(self, change=True, allow_degrade=False) -> int:
        """
        Evaluate the current tier based on activity during the last week.
        :param change: Whether to allow the function to change the channel based on the results
        :param allow_degrade: Whether to allow the channel to go down in tiers
        :return: The evaluated tier
        """
        authors = await self._get_last_week_authors_value()
        total_value = 0
        for author_id, value in authors.items():
            total_value += value
        tier = 0
        for i, threshold in enumerate(self._tier_thresholds_lengths.keys()):
            if total_value >= threshold:
                tier = i + 1
        if not allow_degrade and tier < self.settings.get('tier'):
            tier = self.settings.get('tier')
        if change and tier != self.settings.get('tier'):
            embed = self._get_tier_change_embed(tier)
            self.settings['tier'] = tier
            await self.channel.send(embed=embed)
        return tier

    async def evaluate_state(self):
        marked = self.get_flag('MARKED')
        archived = self.get_flag('ARCHIVED')
        if marked:
            archivable = self.get_archivable()
            if archivable and self.can_delete():
                await self.channel.delete(reason='Expired from inactivity')
            elif archivable:
                await self.set_archive(True)
        elif not archived:
            if await self.get_markable():
                await self.set_marked(True)

    async def post_archive_message(self, content=None, *, embed=None, view=None):
        message_id = self.settings.get('archive_message_id')
        message = None
        if message_id:
            message = await self.channel.fetch_message(message_id)
        if not message:
            message = await self.channel.send(content=content, embed=embed, view=view)
        await message.edit(content=content, view=view, embed=embed)
        self.settings['archive_message_id'] = message.id

    async def get_markable(self) -> bool:
        """
        Returns whether the channel is eligible to be marked for archival
        """
        if self.channel.last_message_id:
            last_message = await self.channel.fetch_message(self.channel.last_message_id)
        else:
            last_message = None
        if last_message is None:
            time = self.channel.created_at
        else:
            time = last_message.created_at
        return time < self.oldest_allowed

    def get_archivable(self) -> bool:
        """
        Returns whether the channel is ready to be archived
        """
        now = datetime.datetime.now().astimezone()
        marked = 'MARKED' in self.flags
        default = now + datetime.timedelta(days=1)
        archive_at_raw = self.settings.get('archive_at')
        if archive_at_raw:
            archive_at = datetime.datetime.fromisoformat(archive_at_raw)
        else:
            archive_at = default
        timing = archive_at < now
        return marked and timing

    def can_delete(self) -> bool:
        return self.settings.get('tier') == 1

    def _get_tier_change_embed(self, tier: int) -> discord.Embed:
        cur_tier = self.settings.get('tier')
        if tier == cur_tier:
            raise ValueError('Tier can not be the same value as the current tier')
        lower = tier < cur_tier
        if lower:
            embed = discord.Embed(
                colour=discord.Colour.red(),
                title=f'Tier decreased to {tier}!'
            )
        else:
            embed = discord.Embed(
                colour=discord.Colour.green(),
                title=f'Tier increased to {tier}!'
            )
        embed.description = f'New idle timer is: {self.tier_duration(tier).days} days'
        return embed

    def _get_marked_embed(self) -> discord.Embed:
        cur_tier = self.settings.get('tier')
        t = self.archive_time
        word = 'archived' if cur_tier > 1 else 'deleted'
        embed = discord.Embed(
            colour=discord.Colour.red(),
            title=f'⚠Flagged to be {word.capitalize()}⚠',
            description=(
                f'This channel has been flagged due to inactivity. The channel will be {word} '
                f'<t:{int(t.timestamp())}:R> for later retrieval, assuming an admin does not remove it.'
            )
        )
        embed.add_field(
            name=f'{word.capitalize()[:-1]} Time',
            value=f'<t:{int(t.timestamp())}:f>'
        )
        return embed

    def _get_saved_embed(self) -> discord.Embed:
        cur_tier = self.settings.get('tier')
        word = 'Archive' if cur_tier > 1 else 'Deletion'
        if self.get_flag('ARCHIVED'):
            embed = discord.Embed(
                colour=discord.Colour.green(),
                title='Channel Restored',
                description=f'Channel restored at {cur_tier} tier.'
            )
        else:
            embed = discord.Embed(
                colour=discord.Colour.green(),
                title=f'{word} Aborted',
                description=f'{word} was successfully aborted.'
            )
        return embed


class VoiceChannel(Channel):
    channel_type = 'private_voice'
    _default_settings = {
        'owner': None,
        'template': None
    }

    def __init__(self, manager: 'ChannelManager', data: dict):
        super().__init__(manager, data)

    def can_delete(self) -> bool:
        ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
        return len(self.channel.members) == 0 and ago <= self.channel.created_at

    def can_neutralize(self) -> bool:
        return self.owner in self.channel.members

    @property
    def owner(self) -> Optional[discord.Member]:
        owner_id = self.settings.get('owner')
        if owner_id:
            return self.channel.guild.get_member(owner_id)
        return None

    async def neutralize(self):
        self.settings['owner'] = None
        await self.channel.edit(name=f'<Neutral> {self.channel.name}')

    async def apply_template(self, template: 'VoiceTemplate'):
        await self.channel.edit(
            name=template.name,
            nsfw=template.nsfw
        )
        await self.update_permissions(template)

    async def update_permissions(self, template: 'VoiceTemplate'):
        for target, perms in template.permissions:
            await self._update_perm(target, perms)

    async def _update_perm(self, target: Union[discord.Member, discord.Role], overwrites: discord.PermissionOverwrite):
        await self.channel.set_permissions(target, overwrite=overwrites)


Channel_Dict = {
    Channel.channel_type: Channel,
    TopicChannel.channel_type: TopicChannel,
    VoiceChannel.channel_type: VoiceChannel
}
