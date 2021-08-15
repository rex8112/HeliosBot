import asyncio
import datetime
import discord
import sqlite3
from discord import colour

from discord.ext import tasks, commands
from tools.database import db

def is_not_banned():
    async def predicate(ctx):
        return db.is_not_banned(ctx.author)
    return commands.check(predicate)

class TopicChannel:
    """A class that handles the specifics of a card.

    Parameters
    ------------
    bot: :class:`discord.Bot`
        The discord bot instance, Client would probably work too.
    channel: :class:`discord.TextChannel`
        Text channel related to this topic.
    description: :class:`str`
        Channel description.
    created_by: :class:`discord.User`
        The author of this topic.
    removal_date: :class:`datetime.date`
        The date the channel will be removed, if any.
    tier: :class:`int`
        The tier of this channel.
    pinned: :class:`bool`
        If this channel is pinned to the top of the sort.
    archive: :class:`bool`
        If this channel has been archived.
        """

    __slots__ = (
        'bot', 'channel', 'guild', 'name', 'description', 'removal_date', 'created_by',
        'tier', 'pinned', 'archive'
    )

    tier_durations ={
        1: datetime.timedelta(days=1),
        2: datetime.timedelta(days=14),
        3: datetime.timedelta(days=30),
        4: datetime.timedelta(days=90)
    }

    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.channel = kwargs.get('channel')
        self.name = kwargs.get('name', '')
        self.description = kwargs.get('description', 'Discussion related to the channel.')
        self.removal_date = kwargs.get('removal_date')
        self.created_by = kwargs.get('created_by')
        self.tier = kwargs.get('tier', 1)
        self.pinned = kwargs.get('pinned', False)
        self.archive = kwargs.get('archive', False)

        if self.channel:
            self.guild = self.channel.guild
        else:
            self.guild = None
        if self.channel is None:
            print(f'CAN NOT FIND {self.name} CHANNEL!!!')

    @staticmethod
    def from_guild(bot, guild: discord.Guild):
        topics = db.get_topic(guildID=guild.id)
        filled_topics = []
        for x in topics:
            try:
                filled_topics.append(TopicChannel.from_data(bot, x))
            except ValueError:
                continue
        final = filled_topics
        return final

    @classmethod
    def from_data(cls, bot, data):
        date = data['pendingRemovalDate']
        if date:
            date = date.replace(tzinfo=datetime.timezone.utc)
            
        return cls(
            bot,
            channel=bot.get_channel(data['channelID']),
            created_by=bot.get_user(data['creatorID']),
            removal_date=date,
            tier=data['tier'],
            pinned=bool(data['pinned']),
            archive=bool(data['archive']),
            description=data['description'],
            name=data['name']
        )

    @classmethod
    def from_channel(cls, bot, channel):
        try:
            data = db.get_topic(channelID=channel.id, guildID=channel.guild.id)[0]
            return TopicChannel.from_data(bot, data)
        except IndexError:
            return None

    def set_channel(self, channel):
        self.channel = channel
        if self.channel:
            self.guild = self.channel.guild
        else:
            self.guild = None

    def get_description(self):
        return (
            f'{self.description} | '
            f'{f"Tier {self.tier}" if not self.archive else "Archived"} '
            f'{"| Pending Archive" if self.removal_date else ""}'
        )
    
    def get_name(self):
        self.name = self.name.replace('_n_shit', '')
        if self.archive:
            prefix = '📕'
        elif self.removal_date:
            prefix = '🛑'
        else:
            prefix = ''
        
        return f'{prefix}{self.name}_n_shit'

    def save(self):
        db.set_topic(
            self.channel.id,
            self.guild.id,
            name=self.name,
            description=self.description,
            tier=self.tier,
            pendingRemovalDate=self.removal_date,
            pinned=int(self.pinned),
            archive=int(self.archive)
        )

    @classmethod
    async def new(cls, bot, name, guild, author):
        name = name.replace(' ', '_')
        server_data = db.get_server(guild)
        category = guild.get_channel(server_data['topicCategory'])
        topic = cls(
            bot,
            name=name,
            created_by=author
        )
        channel = await category.create_text_channel(name=f'{name}_n_shit', topic=topic.get_description())
        topic.set_channel(channel)
        db.add_topic(guild.id, channel.id, author.id)
        topic.save()
        return topic

    def calculate_removal_date(self):
        today = datetime.datetime.now()
        removal_date = today + datetime.timedelta(days=1)
        return removal_date

    async def flag_channel(self, removal_date: datetime.date):
        self.removal_date = removal_date
        self.save()
        embed = discord.Embed(
            title='⚠ Flagged to be Archived ⚠',
            colour=discord.Color.red(),
            description=(
                'This channel has been flagged due to inactivity. '
                'The channel will be archived for later retrieval, assuming an admin does not '
                'remove it. \n'
                'If you wish to remove this, please use `-save` in this channel.'
            )
        )
        embed.add_field(name='Archive Time', value=self.removal_date.strftime('%H:%M %m/%d/%y Central Time'))
        await self.channel.edit(name=self.get_name(), topic=self.get_description())
        await self.channel.send(embed=embed)

    async def delete_channel(self, remove_channel=False):
        db.delete_topic(self.channel.id)
        if remove_channel:
            await self.channel.delete()

    async def archive_channel(self):
        self.archive = True
        self.removal_date = None
        await self.channel.edit(
            name=self.get_name(),
            topic=self.get_description()
        )
        self.save()
        embed = discord.Embed(
            title='Topic Archived',
            description='Topic will remain in stasis until further notice.',
            colour=discord.Colour.dark_gray()
        )
        await self.channel.send(embed=embed)
        server_data = db.get_server(self.guild)
        if server_data['archiveCategory']:
            category = self.guild.get_channel(int(server_data['archiveCategory']))
            if category:
                await self.channel.edit(category=category, sync_permissions=True)

    async def restore_channel(self):
        if self.removal_date:
            embed = discord.Embed(
                title='Archive Aborted',
                colour=discord.Colour.green(),
                description='Archive was succesfully aborted..'
            )
        elif self.archive:
            embed = discord.Embed(
                title='Topic Restored',
                description=f'Topic has been restored at tier **{self.tier}**.',
                colour=discord.Colour.green()
            )
        self.archive = False
        self.removal_date = None
        server_data = db.get_server(self.guild)
        if server_data['topicCategory']:
            category = self.guild.get_channel(int(server_data['topicCategory']))
            await self.channel.edit(
                name=self.get_name(),
                topic=self.get_description(),
                category=category,
                sync_permissions=True
            )
        else:
            await self.channel.edit(
                name=self.get_name(),
                topic=self.get_description()
            )
        self.save()
        try:
            await self.channel.send(embed=embed)
        except NameError:
            pass


class Topic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.topic_checker.start()

    async def tier_checker(self):
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        for g in self.bot.guilds:
            topics = TopicChannel.from_guild(self.bot, g)
            for topic in topics:
                users = []
                if topic.removal_date or topic.archive:
                    continue
                async for message in topic.channel.history(limit=200,after=week_ago):
                    if message.author not in users and not message.author.bot:
                        users.append(message.author)
                threshold = topic.tier * 3
                if len(users) >= threshold and topic.tier < 4:
                    topic.tier += 1
                    embed = discord.Embed(
                        title='⭐ Tier Increased ⭐',
                        colour=discord.Colour.green(),
                        description=(
                            f'{topic.channel.mention} tier has increased to tier {topic.tier}. '
                            f'It now takes `{TopicChannel.tier_durations[topic.tier].days}` days of inactivity to be flagged.'
                        )
                    )
                    await topic.channel.edit(
                        topic=topic.get_description()
                    )
                    await topic.channel.send(embed=embed)
                    topic.save()

    @tasks.loop(hours=1.0)
    async def topic_checker(self):
        for g in self.bot.guilds:
            topics = TopicChannel.from_guild(self.bot, g)
            for topic in topics:
                if topic.archive:
                    continue
                now = discord.utils.utcnow()
                if topic.removal_date:
                    if now >= topic.removal_date:
                        await topic.archive_channel()
                else:
                    time = discord.utils.utcnow()
                    try:
                        async for last_message in topic.channel.history(limit=1):
                            time = last_message.created_at
                    except AttributeError:
                        pass
                    if now - time > TopicChannel.tier_durations[topic.tier]:
                        await topic.flag_channel(topic.calculate_removal_date())
                        await self.sort_topics(topic.guild)
        await self.tier_checker()

    @topic_checker.before_loop
    async def before_topic_checker(self):
        await self.bot.wait_until_ready()

    @commands.command()
    async def topic(self, ctx, *, game_name):
        """Create a new topic channel"""
        if not db.is_not_banned(ctx.author):
            return
        topics = TopicChannel.from_guild(self.bot, ctx.guild)
        topic_names = [x.name.lower() for x in topics]
        if game_name.lower() in topic_names:
            index = topic_names.index(game_name.lower())
            embed = discord.Embed(
                title='This channel already exists.',
                colour=discord.Colour.red(),
                description=f'{topics[index].channel.mention}\nIf you can not see the channel, try running `-archive` to see currently archived channels.'
            )
            await ctx.send(embed=embed)
        else:
            new_topic = await TopicChannel.new(self.bot, game_name, ctx.guild, ctx.author)
            embed = discord.Embed(
                title=f'{new_topic.get_name()} has been created',
                colour=discord.Color.green(),
                description=f'This channel starts off at tier 1, it will be marked for deletion after {TopicChannel.tier_durations[1].days} days of inactivity.'
            )
            await new_topic.channel.send(embed=embed)
            await self.sort_topics(ctx.guild)

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    async def pin_topic(self, ctx):
        """Pin the current topic channel to the top"""
        topic = TopicChannel.from_channel(self.bot, ctx.channel)
        if topic.pinned:
            topic.pinned = False
            await ctx.send('Topic Unpinned')
        else:
            topic.pinned = True
            await ctx.send('Topic Pinned')
        topic.save()
        await self.sort_topics(topic.guild)

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    async def set_tier(self, ctx, tier: int):
        """Sets the current tier of the topic channel"""
        if not db.is_not_banned(ctx.author):
            return
        topic = TopicChannel.from_channel(self.bot, ctx.channel)
        if 1 <= tier and tier <= 4:
            topic.tier = int(tier)
            await topic.channel.edit(topic=topic.get_description())
            topic.save()

    @commands.command()
    async def save(self, ctx):
        """Saves a channel from being archived or removes a channel from the archive"""
        if not db.is_not_banned(ctx.author):
            return
        topic = TopicChannel.from_channel(self.bot, ctx.channel)
        await topic.restore_channel()
        await self.sort_topics(ctx.guild)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def archive_topic(self, ctx):
        if not db.is_not_banned(ctx.author):
            return
        topic = TopicChannel.from_channel(self.bot, ctx.channel)
        await topic.archive_channel()

    @commands.command()
    @commands.guild_only()
    async def archive(self, ctx):
        """View/Hide archived category."""
        data = db.get_server(ctx.guild)
        category = ctx.guild.get_channel(data['archiveCategory'])
        if category:
            if category.overwrites.get(ctx.author):
                overwrites = None
                embed = discord.Embed(title='Archive Hidden', colour=discord.Colour.dark_gray())
            else:
                overwrites = discord.PermissionOverwrite(view_channel=True)
                embed = discord.Embed(title='Archive Shown', colour=discord.Colour.green())
            await category.set_permissions(ctx.author, overwrite=overwrites)
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    async def category(self, ctx, auto_add = False):
        """Used to set the category for topic channels."""
        server_data = db.get_server(ctx.guild)
        category = ctx.channel.category
        if server_data['topicCategory'] != category.id:
            topics = TopicChannel.from_guild(self.bot, ctx.guild)
            for topic in topics:
                if topic.guild == ctx.guild:
                    topic.delete_channel()
            db.update_server(ctx.guild, category.id, server_data['quotesChannel'], server_data['archiveCategory'])
            if auto_add:
                for channel in category.channels:
                    db.add_topic(ctx.guild.id, channel.id, ctx.author.id)
                await self.sort_topics(ctx.guild)
            await ctx.send('Category Set')

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    async def set_archive(self, ctx, category_id):
        server_data = db.get_server(ctx.guild)
        category = ctx.guild.get_channel(int(category_id))
        db.update_server(ctx.guild, server_data['topicCategory'], server_data['quotesChannel'], category.id)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def command_ban(self, ctx, member: discord.Member):
        """Ban someone from using bot features"""
        if db.is_not_banned(member):
            db.add_ban(member)
            await ctx.send(f'{member.display_name} Banned from bot controls.')
        else:
            db.del_ban(member)
            await ctx.send(f'{member.display_name} Unbanned from bot controls.')

    @commands.command()
    @commands.has_guild_permissions(manage_channels=True)
    async def delete_topic(self, ctx):
        """Deletes the current topic channel immediately"""
        if not db.is_not_banned(ctx.author):
            return
        try:
            topic = TopicChannel.from_channel(self.bot, ctx.channel)
            await topic.delete_channel(remove_channel=True)
        except:
            await ctx.send('This channel is not a topic channel')

    async def sort_topics(self, guild):
        server_data = db.get_server(guild)
        category = guild.get_channel(server_data['topicCategory'])
        topics_unfiltered = [TopicChannel.from_channel(self.bot, x) for x in category.channels]
        if None in topics_unfiltered:
            await self.check_for_dirty_topics(guild)
            topics_unfiltered = [TopicChannel.from_channel(self.bot, x) for x in category.channels]
        topics = list(filter(lambda x: x, topics_unfiltered))
        topics = sorted(topics, key=lambda x: x.channel.name)
        topics = sorted(topics, key=lambda x: x.pinned or x.archive, reverse=True)
        for i, topic in enumerate(topics):
            await topic.channel.edit(
                position=i
            )
            await asyncio.sleep(1)

    async def check_for_dirty_topics(self, guild):
        server_data = db.get_server(guild)
        category = guild.get_channel(server_data['topicCategory'])
        for c in category.channels:
            topic = TopicChannel.from_channel(self.bot, c)
            if topic is None:
                db.add_topic(guild.id, c.id, self.bot.user.id)
                topic = TopicChannel.from_channel(self.bot, c)
                name = c.name.replace('_n_shit', '')
                topic.name = name
                topic.save()
                await topic.restore_channel()
                embed = discord.Embed(
                    title='This channel was created poorly.',
                    description=f'This channel still works but try using `-topic {name}` next time. Anyone can do that and will not require a moderators touch.',
                    colour=discord.Colour.red()
                )
                await topic.channel.send(embed=embed)

def setup(bot):
    bot.add_cog(Topic(bot))
