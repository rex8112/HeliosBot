import datetime
from typing import Union
import discord
import sqlite3
import os, os.path
import random
import asyncio

from discord.ext import tasks, commands
from tools.database import db

def is_not_banned():
    async def predicate(ctx):
        return db.is_not_banned(ctx.author)
    return commands.check(predicate)

class Quote:
    def __init__(self, bot):
        self.bot = bot
        self.author = None
        self.content = None
        self.image = None
        self.id = None
        self.speakers = []

    image_path_prefix = './quote_images'

    def set_author(self, author):
        if isinstance(author, (discord.Member, discord.User)):
            self.author = author
        else:
            self.author = self.bot.get_user(author)

    def set_content(self, content):
        self.content = content

    def set_image(self, image):
        self.image = image

    def add_speaker(self, speaker: Union[str, list]):
        if isinstance(speaker, list):
            for s in speaker:
                self.speakers.append(str(s))
        else:
            self.speakers.append(str(speaker))
        db.update_quote(
            self.id,
            author=self.author,
            content=self.content,
            image=self.image,
            jump=self.jump,
            speakers='/'.join(self.speakers)
        )

    def add_quote(self, message: discord.Message) -> bool:
        self.author = message.author
        self.content = message.content
        self.jump = message.jump_url
        mentions = message.mentions
        for m in mentions:
            self.speakers.append(m.id)
        for attachment in message.attachments:
            self.image = attachment.url
        if self.content or self.image:
            speaker_string = '/'.join(str(x) for x in self.speakers)
            if not speaker_string:
                speaker_string = None
            self.id = db.add_quote(self.author, content=self.content, jump=self.jump, image=self.image, speakers=speaker_string)
            return True
        else:
            return False

    def get_embed(self):
        description = f'{self.content}\n\n[Jump Link]({self.jump})' if self.content else f'[Jump Link]({self.jump})'
        embed = discord.Embed(
                title=f'{self.id}. Quote submitted by {self.author}',
                description=description,
                colour=discord.Colour.orange()
            )
        embed.set_footer(text=', '.join(str(x) for x in self.speakers) if self.speakers else '')
        if self.image:
            embed.set_image(url=self.image)
        return embed

    @staticmethod
    def get_quote(bot, id = None, author = None, speaker=None, jump=None):
        fetch = db.get_quote(id=id, author=author, speaker=speaker, jump=jump)
        if fetch:
            quote = random.choice(fetch)
        else:
            return None
        q = Quote(bot)
        q.id = quote['id']
        q.content = quote['content']
        q.jump = quote['jump']
        q.author = bot.get_user(quote['author'])
        q.image = quote['image']
        if quote['speakers']:
            q.speakers = [bot.get_user(int(x)) for x in quote['speakers'].split('/')]
        else:
            q.speakers = []
        return q


    def delete(self):
        db.del_quote(self.id)

class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        data = db.get_server(message.guild)
        if message.channel.id == data['quotesChannel']:
            q = Quote(self.bot)
            q.add_quote(message)
            try:
                await message.add_reaction('✅')
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        data = db.get_server(payload.guild_id)
        if payload.channel_id == data['quotesChannel']:
            jump = f'https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id}'
            q = Quote.get_quote(self.bot, jump=jump)
            q.delete()


    @commands.group()
    async def quote(self, ctx):
        """Get a random quote if no arguments are given."""
        if ctx.invoked_subcommand is None:
            q = Quote.get_quote(self.bot)
            await ctx.send(embed=q.get_embed())

    @quote.command()
    async def searchid(self, ctx, number: int):
        """Search by ID."""
        q = Quote.get_quote(self.bot, id=number)
        if q:
            await ctx.send(embed=q.get_embed())
        else:
            embed = discord.Embed(
                title='No Quote Found',
                colour=discord.Colour.red()
            )
            await ctx.send(embed=embed)

    @quote.command()
    async def searchspeaker(self, ctx, speaker: discord.Member):
        """Search by speaker."""
        q = Quote.get_quote(self.bot, speaker=speaker)
        if q:
            await ctx.send(embed=q.get_embed())
        else:
            embed = discord.Embed(
                title='No Quote Found',
                colour=discord.Colour.red()
            )
            await ctx.send(embed=embed)

    @quote.command()
    async def searchposter(self, ctx, author: discord.Member):
        """Search by poster."""
        q = Quote.get_quote(self.bot, author=author)
        if q:
            await ctx.send(embed=q.get_embed())
        else:
            embed = discord.Embed(
                title='No Quote Found',
                colour=discord.Colour.red()
            )
            await ctx.send(embed=embed)

    @quote.command()
    async def new(self, ctx, message: discord.Message):
        """Add a new quote if the bot missed it."""
        q = Quote(self.bot)
        await q.add_quote(message)
        if not q.speakers:
            embed = discord.Embed(
                title=f'Apologies {ctx.author.display_name}',
                description=(
                    'I can not seem to find the speaker of this quote. Could you please tell me? '
                    'If there is more than one, seperate them with commas. Please only do this if '
                    'the speaker has a discord account that you can mention.'
                ),
                colour=discord.Colour.red()
            )
            base_message = await ctx.send(embed=embed)
            try:
                value_message = await self.bot.wait_for('message', timeout=60.0, check=lambda message: message.author.id == ctx.author.id and message.channel.id == ctx.channel.id)
                if value_message.mentions:
                    q.add_speaker(value_message.mentions)
                    await value_message.delete()
                    embed.title = 'Thank you'
                    embed.description = f'{", ".join(q.speakers)} added as speaker{"s" if len(q.speakers) > 1 else ""}.'
                    await base_message.edit(embed=embed, delete_after=5)

            except asyncio.TimeoutError:
                await base_message.delete()
    
    @quote.command()
    @commands.has_guild_permissions(administrator=True)
    async def set_quotes_channel(self, ctx, channel: discord.TextChannel, walk=False):
        """Set which channel is automatically watched for new quotes."""
        data = db.get_server(channel.guild)
        db.update_server(channel.guild, data['topicCategory'], channel.id)
        if walk:
            start = datetime.datetime.now()
            embed = discord.Embed(
                title='Preparing Batch Load',
                description='You really gonna make me do this?',
                colour=discord.Colour.orange()
            )
            await ctx.send(embed=embed)
            async with ctx.typing():
                count = 0
                errors = 0
                error_log = ''
                async for message in channel.history(limit=None, oldest_first=True):
                    q = Quote(self.bot)
                    try:
                        if q.add_quote(message):
                            count += 1
                    except Exception as e:
                        errors += 1
                        error_log += (
                            f'{message.jump_url}\n{type(e).__name__}: {e}'
                            '\n----------------------\n'
                        )
                if error_log:
                    with open(f'./{channel.guild.name}_batch_load_error.txt', 'w') as log_file:
                        log_file.write(error_log)
                duration = datetime.datetime.now() - start
                embed = discord.Embed(
                    title='Batch Load Complete',
                    description=f'Quotes loaded: **{count}**\nErrors: **{errors}**\nCompleted in **{duration.seconds}** seconds.',
                    colour=discord.Colour.green()
                )
                await ctx.send(embed=embed)
                embed = discord.Embed(
                    title='Quotes Recorded',
                    description=(
                        'Everything before this point has now been saved into '
                        'the database. A checkmark will be placed on all message '
                        'hereafter if I am running properly and see it. If you '
                        'do not see it, then be ready to run `-quote new` when '
                        'I am back online.'
                    ),
                    colour=discord.Colour.green()
                )
                await channel.send(embed=embed)








def setup(bot):
    bot.add_cog(Quotes(bot))