import datetime
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from helios import ChannelManager, HeliosBot


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
        return cls(manager, data)

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
    return datetime.datetime.now() + datetime.timedelta(hours=30)


class TopicChannel(Channel):
    channel_type = 'topic'
    _default_settings = {
        'tier': 0,
        'saves_in_row': 0,
        'creator': None,
        'archive_at': None,
        'archive_message_id': None,
        **super()._default_settings
    }
    _allowed_flags = [
        'MARKED',
        'ARCHIVED',
        *super()._allowed_flags
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
        :return: A naive timezone that I think is in local time
        """
        delta = list(self._tier_thresholds_lengths.values())[self.settings.get('tier') - 1]
        now = datetime.datetime.now()
        return now - delta

    async def _get_last_week_authors_value(self) -> dict[int, int]:
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        authors = {}
        async for msg in self.channel.history(after=week_ago):
            author = msg.author
            if not author.bot:
                authors[author.id] = 0.05 + authors.get(author.id, 1)
        return authors

    async def set_marked(self, state: bool, post=True) -> None:
        """
        Set whether the channel is marked for archival.
        :param state: The state to set it to
        :param post: Whether to make/edit a post about it
        """
        self.set_flag('MARKED', state)
        if state:
            self.settings['archive_at'] = _get_archive_time()
        else:
            self.settings['archive_at'] = None
        if post:
            if state:  # TODO add marked embeds and views
                message = await self.channel.send(content='Beep Boop: Need Embeds and View Setup')
                self.settings['archive_message_id'] = message.id
            else:
                message_id = self.settings.get('archive_message_id')
                message = None
                if message_id:
                    message = await self.channel.fetch_message(message_id)
                if not message:
                    message = await self.channel.send(content='Beep Boop: Need Embeds and View Setup')
                await message.edit(view=None, embed=None)
                self.settings['archive_message_id'] = message.id

    async def set_archive(self, state: bool, post=True) -> None:
        self.settings['archive_at'] = None
        if state:
            await self.set_marked(False, post=False)
        # TODO Post archive messages and move to category found in Server settings

    async def save_channel(self, interaction: discord.Interaction = None):
        post = interaction is None
        if self.get_flag('ARCHIVED'):
            await self.set_archive(False, post=post)
        elif self.get_flag('MARKED'):
            await self.set_marked(False, post=post)
        # TODO Use interaction to post save embed

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
            self.settings['tier'] = tier
            embed = self._get_tier_change_embed(tier)
            await self.channel.send(embed=embed)
        return tier

    async def get_markable(self) -> bool:
        """
        Returns whether the channel is eligible to be marked for archival
        """
        last_message = await self.channel.fetch_message(self.channel.last_message_id)
        return last_message.created_at < self.oldest_allowed

    def get_archivable(self) -> bool:
        """
        Returns whether the channel is ready to be archived
        """
        now = datetime.datetime.now()
        marked = 'MARKED' in self.flags
        timing = self.settings.get('archive_at', now + datetime.timedelta(days=1)) < now
        return marked and timing

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
        embed.description = f'New idle timer is: {self._tier_thresholds_lengths.get(tier).days} days'
        return embed


Channel_Dict = {
    Channel.channel_type: Channel,
    TopicChannel.channel_type: TopicChannel
}
