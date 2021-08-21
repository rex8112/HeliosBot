import discord
import datetime

from discord.ext import tasks, commands
from discord.ext.commands.errors import MemberNotFound
from discordtools import WaitFor
from tools.database import db
from views.confirmation import ConfirmationView
from sqlite3 import IntegrityError

class VoiceChannel:
    def __init__(self, bot):
        self.bot = bot
        self.voice_channel = None
        self.text_channel = None
        self.guild = None
        self.creator = None
        self.delete_time = None
        self.whitelist = False
        self.people = []

    @staticmethod
    def get_all(bot):
        voices = []
        datas = db.get_voice()
        for data in datas:
            voice = VoiceChannel(bot)
            voice.load(voiceID=data['voiceID'])
            voices.append(voice)
        return voices

    def load(self, **options):
        data = db.get_voice(**options)[0]
        if not data:
            raise ValueError('No Voice')
        self.voice_channel = self.bot.get_channel(int(data['voiceID']))
        self.guild = self.voice_channel.guild
        self.text_channel = self.guild.get_channel(int(data['textID']))
        self.creator = self.guild.get_member(int(data['creator']))
        self.delete_time = data['deleteTime']
        self.whitelist = bool(data['whitelist'])
        self.people = (self.guild.get_member(int(x)) for x in data['people'].split(','))

    async def new(self, guild, name, creator: discord.Member, whitelist: bool, people: list):
        MINUTES_TO_DELETE = 10

        self.guild = guild
        self.creator = creator
        self.whitelist = whitelist
        self.delete_time = datetime.datetime.now() + datetime.timedelta(minutes=MINUTES_TO_DELETE)
        self.people = people
        private_category = None # Get Category
        for category in guild.categories:
            if category.name == 'Private Channels':
                private_category = category

        allow_permissions = discord.PermissionOverwrite( # Set Permissions
            view_channel = True,
            connect = True
        )
        deny_permissions = discord.PermissionOverwrite(
            view_channel = False,
            connect = False
        )
        if whitelist: # Build overwrites dict for discord
            overwrites = {
                guild.default_role: deny_permissions
            }
            for p in people:
                overwrites[p] = allow_permissions
        else:
            overwrites = {
                guild.default_role: allow_permissions
            }
            for p in people:
                overwrites[p] = deny_permissions
        if private_category: # Choose whether to make it in category or guild
            c = private_category
        else:
            c = guild
        topic = f'Private text channel coupled with the voice channel below.'
        self.text_channel = await c.create_text_channel(
            name,
            overwrites=overwrites,
            topic=topic,
            reason=f'Created by {creator}'
        )
        self.voice_channel = await c.create_voice_channel(
            name,
            overwrites=overwrites,
            reason=f'Created by {creator}'
        )

        embed = discord.Embed(
            title=f'{name} Created Successfully',
            description=(
                f'This channel will persist for {MINUTES_TO_DELETE} minutes or until everyone is gone, whichever comes last.\n'
                'Keep in mind, Administrators can still see all of these channels.'
            ),
            colour=discord.Colour.green()
        )
        embed.add_field(
            name='Creator',
            value=f'{self.creator.mention}'
        )
        people_string = '\n'.join(e.mention for e in self.people)
        embed.add_field(
            name=f'{"Allowed" if self.whitelist else "Blocked"} People',
            value=people_string if people_string else 'None'
        )
        await self.text_channel.send(embed=embed)
        db.add_voice(
            self.creator.id,
            self.voice_channel.id,
            self.text_channel.id,
            self.whitelist,
            filter(lambda x: bool(x), (x.id if x else x for x in self.people)),
            self.delete_time
        )
        try:
            db.add_last(self.creator.id)
        except IntegrityError:
            pass
        db.set_last(self.creator.id, name, self.whitelist, filter(lambda x: bool(x), (x.id if x else x for x in self.people)))

    async def check_delete(self):
        if not self.voice_channel.members and datetime.datetime.now() > self.delete_time:
            await self.delete()

    async def delete(self):
        db.delete_voice(self.voice_channel.id)
        try:
            await self.text_channel.delete()
        except (discord.NotFound, discord.Forbidden, AttributeError):
            pass
        try:
            await self.voice_channel.delete()
        except (discord.NotFound, discord.Forbidden, AttributeError):
            pass


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_checker.start()

    @tasks.loop(seconds=10)
    async def voice_checker(self):
        voices = VoiceChannel.get_all(self.bot)
        for voice in voices:
            await voice.check_delete()

    @voice_checker.before_loop
    async def before_voice_checker(self):
        await self.bot.wait_until_ready()

    @commands.group()
    @commands.guild_only()
    async def voice(self, ctx):
        """Use -help voice for more info."""
        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild.me in message.mentions:
            member = message.author
            if member.voice:
                vc = member.voice.channel
                if vc:
                    embed = discord.Embed(
                        title=f'Mention Everyone in {vc.name}?',
                        colour=discord.Colour.orange()
                    )
                    view = ConfirmationView()
                    members_to_mention = vc.members
                    q_message = await message.channel.send(embed=embed, view=view)
                    confirmed = await view.wait_for_answer()
                    if confirmed:
                        await q_message.delete()
                        await message.channel.send(
                            f'{member.mention} pinged:\n' + ' '.join(e.mention for e in members_to_mention)
                        )
                    else:
                        await q_message.delete()

    @voice.command()
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def new(self, ctx):
        """Create a new private channel with the desired settings."""
        if db.get_voice(creator=ctx.author.id):
            embed = discord.Embed(
                title='Do you really need another one?',
                colour=discord.Colour.red()
            )
            await ctx.send(embed=embed)
            return
        wait = WaitFor(self.bot, 'message', lambda message: message.author == ctx.author and message.channel == ctx.channel, 30)
        wait.set_messageable(ctx)
        embed = discord.Embed(
            title="Channel Setup",
            colour=discord.Colour.green()
        )
        wait.set_embed(embed)
        last = db.get_last(ctx.author.id)
        redo = True
        make = False
        stage = 0
        
        while redo:
            if last and stage == 0:
                embed.description = (
                    'Would you like to create a `new` configuration or use your `last` one?'
                )
                embed.set_footer(text='Reply with either: new/last')
                value = await wait.run()
                if value:
                    content = value.content
                else:
                    stage = -1
                    continue
                if content == 'new':
                    stage = 1
                elif content == 'last':
                    stage = -2
                else:
                    stage = -1
            elif stage == 0:
                stage = 1

            if stage == 1:
                embed.description = 'What would you like to name the new channel?'
                embed.set_footer(text='Reply with a name between 1 and 100 characters')
                value = await wait.run()
                if value:
                    name = value.content
                    length = len(name)
                    if length > 1 and length < 100:
                        stage = 2
                    else:
                        warning = await wait.messageable.send('Name MUST be within 1 and 100 Characters.')
                        wait.bot_messages.append(warning)
                else:
                    stage = -1
                    continue
            elif stage == 2:
                embed.description = 'Would you like the list of players that you will give in the next step to be a blacklist or a whitelist?'
                embed.set_footer(text='Reply with either: blacklist/whitelist')
                value = await wait.run()
                if value:
                    content = value.content.lower()
                    if content == 'blacklist':
                        whitelist = False
                        stage = 3
                    elif content == 'whitelist':
                        whitelist = True
                        stage = 3
                    else:
                        warning = await wait.messageable.send('Invalid response, if you wish to cancel just wait for half a minute.')
                        wait.bot_messages.append(warning)
                else:
                    stage = -1
                    continue
            elif stage == 3:
                embed.description = f'Enter a space separated list of users to {"whitelist" if whitelist else "blacklist"}.'
                embed.set_footer(text='Reply with a space separated list of user OR reply with 0 to have an empty list')
                value = await wait.run()
                list_of_members = []
                if value:
                    if value.content != '0':
                        content_list = value.content.split(' ')
                        converter = commands.MemberConverter()
                        for raw in content_list:
                            try:
                                result = await converter.convert(ctx, raw)
                            except MemberNotFound:
                                result = None
                            if result:
                                list_of_members.append(result)
                    make = True
                    stage = -1
                else:
                    stage = -1
                    continue
            elif stage == -2:
                await self.last(ctx)
                stage = -1
            elif stage == -1:
                redo = False
        
        if make:
            voice = VoiceChannel(self.bot)
            people = list(list_of_members)
            if whitelist:
                people.append(ctx.author)
            await ctx.message.delete()
            await voice.new(ctx.guild, name, ctx.author, whitelist, people)
        await wait.cleanup()

    @voice.command()
    async def delete(self, ctx):
        """Use this in the text channel of what you want to delete."""
        voice = VoiceChannel(self.bot)
        voice.load(textID=ctx.channel.id)
        if ctx.author == voice.creator or ctx.author.guild_permissions.manage_channels:
            await voice.delete()
        else:
            await ctx.send('You do not have the appropriate permissions to delete this.')

    @voice.command()
    async def last(self, ctx):
        """Create a voice channel based on the last settings used."""
        if db.get_voice(creator=ctx.author.id):
            embed = discord.Embed(
                title='Do you really need another one?',
                colour=discord.Colour.red()
            )
            await ctx.send(embed=embed)
            return
        people = []
        last = db.get_last(ctx.author.id)
        if not last:
            return
        if last['people']:
            for p in last['people'].split(','):
                i = int(p)
                m = ctx.guild.get_member(i)
                people.append(m)
        voice = VoiceChannel(self.bot)
        await ctx.message.delete()
        await voice.new(ctx.guild, last['name'], ctx.author, last['whitelist'], people)

    @voice.command()
    @commands.cooldown(1, 900, type=commands.BucketType.member)
    async def current(self, ctx, name: str):
        """Creates a whitelisted voice channel based on the members in the current vc."""
        if db.get_voice(creator=ctx.author.id):
            embed = discord.Embed(
                title='Do you really need another one?',
                colour=discord.Colour.red()
            )
            await ctx.send(embed=embed)
            return
        channel = ctx.author.voice.channel
        if not channel:
            return
        voice = VoiceChannel(self.bot)
        await ctx.message.delete()
        await voice.new(ctx.guild, name, ctx.author, True, list(channel.members))
        for m in channel.members:
            try:
                await m.move_to(voice.voice_channel, reason='New Channel Created')
            except discord.HTTPException:
                pass

def setup(bot):
    bot.add_cog(Voice(bot))