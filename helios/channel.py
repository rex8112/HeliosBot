import datetime
import json
from typing import TYPE_CHECKING, Optional, Union

import discord

from .database import ChannelModel, update_model_instance
from .views import TopicView, VoiceView

if TYPE_CHECKING:
    from helios import ChannelManager, HeliosBot, HeliosMember
    from .voice_template import VoiceTemplate

MessageType = Union[discord.Message, discord.PartialMessage]


class Channel:
    channel_type = 'basic'
    _default_settings = {}
    _allowed_flags = []

    def __init__(self,
                 manager: 'ChannelManager',
                 data: Union[ChannelModel, dict]):
        """
        A special channel class that will hold all the important functions of that class
        :param manager: The channel manager handling this channel
        :param data: Channel data dict
        """
        self.bot: 'HeliosBot' = manager.bot
        self.manager = manager
        self.channel = None
        self.flags = []
        self._id = None

        self._id = data.id if isinstance(data, ChannelModel) else data.get('id')
        self.channel = self.bot.get_channel(self._id)
        self._new = False

        self.settings = self._default_settings.copy()
        if isinstance(data, ChannelModel):
            self._deserialize(data)
        self.db_entry: Optional[ChannelModel] = data if isinstance(data, ChannelModel) else None

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
            self.db_entry = ChannelModel.create(**self.serialize())
            self._new = False
        else:
            update_model_instance(self.db_entry, self.serialize())
            self.db_entry.save()

    async def delete(self, del_channel=True):
        try:
            if del_channel:
                await self.channel.delete()
        except (discord.Forbidden, discord.HTTPException, discord.NotFound):
            pass
        finally:
            if self._id in self.manager.channels:
                self.manager.channels.pop(self._id)
            self.db_entry.delete_instance()

    def set_flag(self, flag: str, on: bool):
        if flag not in self._allowed_flags:
            raise KeyError(f'{flag} not in {type(self)} allowed flags: {self._allowed_flags}')
        if flag in self.flags and on is False:
            self.flags.remove(flag)
        elif flag not in self.flags and on is True:
            self.flags.append(flag)

    def get_flag(self, flag: str):
        return flag in self.flags

    def _deserialize(self, data: ChannelModel) -> None:
        if self.channel_type != data.type:
            raise TypeError(f'Channel data is of type `{data.type}` '
                            f'not `{self.channel_type}`')
        self.flags = json.loads(data.flags) if data.flags else self.flags
        self.settings = {**self._default_settings, **json.loads(data.settings)}

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'server': self.server.id,
            'type': self.channel_type,
            'settings': json.dumps(self.settings),
            'flags': json.dumps(self.flags)
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
        self._archive_message = None
        self._creator = None

    @property
    def oldest_allowed(self) -> datetime.datetime:
        """
        Get the datetime of how old the last message has to be for the channel to get marked
        :return: An aware datetime that is in local time
        """
        delta = list(self._tier_thresholds_lengths.values())[self.tier - 1]
        now = datetime.datetime.now().astimezone()
        return now - delta

    @property
    def archive_category(self) -> Optional[discord.CategoryChannel]:
        channel_id = self.server.settings.archive_category
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

    @property
    def topic_category(self) -> Optional[discord.CategoryChannel]:
        channel_id = self.server.settings.topic_category
        if channel_id:
            return self.bot.get_channel(channel_id)
        return None

    @property
    def tier(self):
        return self.settings['tier']

    @tier.setter
    def tier(self, value: int):
        self.settings['tier'] = value

    @property
    def saves_in_row(self):
        return self.settings['saves_in_row']

    @saves_in_row.setter
    def saves_in_row(self, value: int):
        self.settings['saves_in_row'] = value

    @property
    def creator(self) -> Optional[discord.Member]:
        if isinstance(self.settings['creator'], list):
            self.settings['creator'] = self.settings['creator'][1]
        if self.settings['creator'] is None:
            return None
        if self._creator and self._creator.id == self.settings['creator']:
            return self._creator
        self._creator = self.server.guild.get_member(self.settings['creator'])
        return self._creator

    @creator.setter
    def creator(self, value: Optional[discord.Member]):
        self._creator = value
        if value is None:
            self.settings['creator'] = value
        else:
            self.settings['creator'] = value.id

    @property
    def archive_at(self):
        if isinstance(self.settings['archive_at'], list):
            self.settings['archive_at'] = self.settings['archive_at'][1]
        if self.settings['archive_at'] is None:
            return None
        return datetime.datetime.fromisoformat(self.settings['archive_at'])

    @archive_at.setter
    def archive_at(self, value: Optional[datetime.datetime]):
        if value is None:
            final_value = value
        elif isinstance(value, str):
            final_value = value
        else:
            final_value = value.isoformat()
        self.settings['archive_at'] = final_value

    @property
    def archive_message(self):
        if isinstance(self.settings['archive_message_id'], list):
            setting = self.settings['archive_message_id'][1]
            self.settings['archive_message_id'] = setting
        if (self._archive_message
                and self._archive_message.id
                == self.settings['archive_message_id']):
            return self._archive_message
        if self.settings['archive_message_id'] is not None:
            return self.channel.get_partial_message(
                self.settings['archive_message_id']
            )
        return None

    @archive_message.setter
    def archive_message(self, value: Optional[MessageType]):
        self._archive_message = value
        if value is None:
            self.settings['archive_message_id'] = value
        else:
            self.settings['archive_message_id'] = value.id

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
            self.archive_at = _get_archive_time().isoformat()
        else:
            self.archive_at = None
        if post:
            if state:
                await self.post_archive_message(embed=self._get_marked_embed(), view=TopicView(self.bot))
            else:
                await self.post_archive_message(embed=self._get_saved_embed())
        if state:
            await self.channel.edit(name=f'🛑{self.channel.name}')
        else:
            if '🛑' in self.channel.name:
                await self.channel.edit(name=self.channel.name.replace('🛑', ''))

    async def set_archive(self, state: bool, post=True) -> None:
        self.set_flag('ARCHIVED', state)
        self.archive_at = None
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
            embed = self._get_saved_embed()
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
            await interaction.response.edit_message(embed=embed, view=None)
        self.archive_message = None

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
        if not allow_degrade and tier < self.tier:
            tier = self.tier
        if change and tier != self.tier:
            embed = self._get_tier_change_embed(tier)
            self.tier = tier
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
        message = self.archive_message
        if type(message) == discord.PartialMessage:
            message = await message.fetch()
        if message is None:
            message = await self.channel.send(content=content, embed=embed,
                                              view=view)
        else:
            await message.edit(content=content, view=view, embed=embed)
        self.archive_message = message

    async def get_markable(self) -> bool:
        """
        Returns whether the channel is eligible to be marked for archival
        """
        if self.channel.last_message_id:
            try:
                last_message = await self.channel.fetch_message(self.channel.last_message_id)
            except discord.NotFound:
                messages = [message async for message in self.channel.history(limit=1)]
                if len(messages) > 0:
                    last_message = messages[0]
                else:
                    last_message = None
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
        archive_at = self.archive_at
        if archive_at is None:
            archive_at = default
        timing = archive_at < now
        return marked and timing

    def can_delete(self) -> bool:
        return self.tier == 1

    def _get_tier_change_embed(self, tier: int) -> discord.Embed:
        cur_tier = self.tier
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
        cur_tier = self.tier
        t = self.archive_at
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
        cur_tier = self.tier
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
        'template_owner': None,
        'template_name': 'NewTemplate'
    }

    def __init__(self, manager: 'ChannelManager', data: dict):
        super().__init__(manager, data)
        self.last_name_change = None
        self._temp_owner: Optional[HeliosMember] = None
        self._owner: Optional[HeliosMember] = None
        self._message = None

    @property
    def owner(self) -> Optional['HeliosMember']:
        if self.settings['owner'] is None:
            return None
        if self._owner and self._owner.id == self.settings['owner']:
            return self._owner
        self._owner = self.server.members.get(self.settings['owner'])
        return self._owner

    @owner.setter
    def owner(self, value: Optional['HeliosMember']):
        self.template_owner = value
        self._owner = value
        if value is None:
            self.settings['owner'] = None
        else:
            self.settings['owner'] = value.member.id

    @property
    def template_owner(self):
        if self.settings['template_owner'] is None:
            return None
        if (self._temp_owner
                and self._temp_owner.id == self.settings['template_owner']):
            return self._temp_owner
        self._temp_owner = self.server.members.get(
            self.settings['template_owner']
        )
        return self._temp_owner

    @template_owner.setter
    def template_owner(self, value):
        self._temp_owner = value
        if value is None:
            return
        else:
            self.settings['template_owner'] = value.member.id

    @property
    def template_name(self) -> str:
        return self.settings['template_name']

    @template_name.setter
    def template_name(self, value: str):
        self.settings['template_name'] = value

    def can_delete(self) -> bool:
        ago = (datetime.datetime.now().astimezone()
               - datetime.timedelta(minutes=5))
        empty = len(self.channel.members) == 0
        before = ago >= self.channel.created_at
        return empty and before

    def can_neutralize(self) -> bool:
        return self.owner and self.owner.member not in self.channel.members

    def next_name_change(self) -> datetime.datetime:
        if self.last_name_change is None:
            return (datetime.datetime.now().astimezone()
                    - datetime.timedelta(minutes=1))
        return self.last_name_change + datetime.timedelta(minutes=15)

    def get_template(self) -> Optional['VoiceTemplate']:
        if self.template_owner:
            templates = list(filter(lambda x: x.name == self.template_name,
                                    self.template_owner.templates))
            if len(templates) > 0:
                return templates[0]
            return None
        return None

    def _get_menu_embed(self) -> discord.Embed:
        owner = self.owner
        template = self.get_template()
        owner_string = ''
        if owner:
            owner_string = f'Owner: {owner.member.mention}'
        private_string = ('This channel **is** visible to everyone except '
                          'those in Denied')
        if template.private:
            private_string = ('This channel **is __not__** visible to anyone '
                              'except admins and those in Allowed')
        embed = discord.Embed(
            title=f'{self.channel.name} Menu',
            description=('Any and all settings are controlled from this '
                         'message.\n'
                         f'{owner_string}\n\n{private_string}'),
            colour=discord.Colour.orange()
        )
        allowed_string = '\n'.join(x.mention
                                   for x in template.allowed.values())
        denied_string = '\n'.join(x.mention
                                  for x in template.denied.values())
        embed.add_field(
            name='Allowed',
            value=allowed_string if allowed_string else 'None'
        )
        embed.add_field(
            name='Denied',
            value=denied_string if denied_string else 'None'
        )
        return embed

    async def update_message(self):
        if self._message is None:
            self._message = await self.channel.send(
                embed=self._get_menu_embed(),
                view=VoiceView(self)
            )
        else:
            await self._message.edit(embed=self._get_menu_embed(),
                                     view=VoiceView(self))

    async def allow(self, member: discord.Member):
        mem, perms = self.get_template().allow(member)
        await self.channel.set_permissions(mem, overwrite=perms)
        await self.get_template().save()
        await self.update_message()

    async def deny(self, member: discord.Member):
        mem, perms = self.get_template().deny(member)
        await self.channel.set_permissions(mem, overwrite=perms)
        await self.get_template().save()
        await self.update_message()

    async def clear(self, member: discord.Member):
        mem, perms = self.get_template().clear(member)
        await self.channel.set_permissions(mem, overwrite=perms)
        await self.get_template().save()
        await self.update_message()

    async def change_name(self, name: str):
        self.last_name_change = datetime.datetime.now().astimezone()
        await self.channel.edit(
            name=name
        )
        template = self.get_template()
        template.name = name
        self.template_name = name
        await self.save()
        await template.save()
        await self.update_message()

    async def neutralize(self):
        self.owner = None
        await self.channel.edit(name=f'<Neutral> {self.channel.name}')
        await self.update_message()

    async def apply_template(self, template: 'VoiceTemplate'):
        await self.channel.edit(
            name=template.name,
            nsfw=template.nsfw
        )
        self.template_name = template.name
        await self.update_permissions(template)

    async def save_template(self):
        template = self.get_template()
        template.name = self.channel.name
        template.nsfw = self.channel.nsfw
        template.allowed.clear()
        template.denied.clear()
        for target, perms in self.channel.overwrites.items():
            if isinstance(target, discord.Member):
                if perms.view_channel:
                    template.allowed[target.id] = target
                elif perms.view_channel is None:
                    ...
                else:
                    template.denied[target.id] = target
        await template.save()

    async def update_permissions(self, template: 'VoiceTemplate'):
        await self.channel.edit(overwrites=template.overwrites)

    async def _update_perm(self, target: Union[discord.Member, discord.Role],
                           overwrites: discord.PermissionOverwrite):
        await self.channel.set_permissions(target, overwrite=overwrites)


Channel_Dict = {
    Channel.channel_type: Channel,
    TopicChannel.channel_type: TopicChannel,
    VoiceChannel.channel_type: VoiceChannel
}
