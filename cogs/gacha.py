import asyncio
import datetime
from typing import List
import discord
import random
import math
from discord import colour
import numpy

from discord.ext import commands, tasks
from tools.database import db
from .theme import GuildTheme, Rank

class Hero:
    """A class that handles the specifics of a card.

    Parameters
    ------------
    member: :class:`discord.Member`
        The member the hero relates to.
    guild_id: :class:`int`
        The id number of the guild the hero is in.
    hero_id: :class:`int`
        The id number of the member the hero relates to.
        """
    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.member = kwargs.get('member')
        if self.member:
            self.guild_id = self.member.guild.id
            self.hero_id = self.member.id
            self.guild = self.member.guild
            self.name = self.member.display_name
            self.username = self.member.name
        else:
            self.guild_id = kwargs.get('guild_id')
            self.hero_id = kwargs.get('hero_id')
            self.username = None
            self.name = None
            self.guild = self.bot.get_guild(self.guild_id)
            if self.guild:
                self.member = self.guild.get_member(self.hero_id)
        self.stars = -1
        self.total = 0
        self.active = False
        self.fresh = False

        try:
            self.load()
        except AttributeError:
            self.new()

    def __eq__(self, other):
        if isinstance(other, Hero):
            return self.guild_id == other.guild_id and self.hero_id == other.hero_id
        else:
            NotImplemented

    def load(self):
        data = db.get_hero(guildID=self.guild_id, heroID=self.hero_id)
        if data:
            data = data[0]
        else:
            raise AttributeError('Hero not found')
        self.guild_id = data['guildID']
        self.hero_id = data['heroID']
        self.stars = int(data['stars'])
        self.active = bool(data['active'])
        self.total = int(data['total'])
        if not self.username:
            self.username = data['name']
            self.name = self.username

    def save(self):
        if not db.get_hero(heroID=self.hero_id, guildID=self.guild_id):
            db.add_hero(self.guild_id, self.hero_id)
        db.set_hero(
            self.guild_id,
            self.hero_id,
            stars=self.stars,
            active=int(self.active),
            name=self.username
        )

    def new(self):
        self.check_stars()
        db.add_hero(self.guild_id, self.hero_id)
        self.save()
        self.fresh = True

    def check_stars(self):
        if self.member:
            theme = GuildTheme(self.member.guild)
            index = theme.get_current_rank_index(self.member)
            if index:
                stars = index + 1
            else:
                stars = 1
        else:
            stars = self.stars if self.stars >= 0 else 0
        if stars != self.stars:
            self.stars = stars 
            return True
        else:
            return False

    def get_stars_string(self):
        stars = ''
        if self.stars > 5:
            stars = f'{self.stars}⭐'
        else:
            for _ in range(self.stars):
                stars += '⭐'
        return stars

    def get_mention(self):
        if self.member:
            return self.member.mention
        else:
            return self.username

    def add_total(self, amount):
        db.add_total_hero(self.guild_id, self.hero_id, amount)

    @staticmethod
    def list_from_guild(bot, guild):
        data = db.get_hero(guildID=guild.id)
        heroes = []
        for d in data:
            hero = Hero(bot, guild_id=d['guildID'], hero_id=d['heroID'])
            heroes.append(hero)
        return heroes

    @staticmethod
    def list_all(bot):
        heroes = []
        data = db.get_hero()
        for d in data:
            hero = Hero(
                bot,
                guild_id=d['guildID'],
                hero_id=d['heroID']
            )
            heroes.append(hero)
        return heroes


class Card:
    def __init__(self, bot, hero, quantity: int, level: int):
        if isinstance(hero, Hero):
            self.hero = hero
        elif isinstance(hero, discord.Member):
            self.hero = Hero(bot, member=hero)
        else:
            raise AttributeError('Incorrect Hero type')
        self.quantity = quantity
        self.level = level

    def __eq__(self, other):
        if isinstance(other, Card):
            return self.hero == other.hero and self.level == other.level
        else:
            NotImplemented

    def __add__(self, other):
        if isinstance(other, Card):
            if self.hero == other.hero and self.level == other.level:
                new_value = self.quantity + other.quantity
                return Card(self.hero.bot, self.hero, new_value, self.level)
            else:
                NotImplemented
        else:
            NotImplemented

    def __iadd__(self, other):
        if isinstance(other, Card):
            if self.hero == other.hero and self.level == other.level:
                self.quantity += other.quantity
            else:
                NotImplemented
        else:
            NotImplemented

    def level_up(self):
        if self.quantity >= 3:
            self.quantity -= 3
            return Card(self.hero.bot, self.hero, 1, self.level + 1)

    def get_embed_info(self):
        """Gets info to put in an discord.Embed field
        
        Returns: (name, value)
        """
        stars = ''
        if self.hero.stars > 5:
            stars = f'{self.hero.stars}⭐'
        else:
            for _ in range(self.hero.stars):
                stars += '⭐'
        name = f'{self.hero.name}'
        value = f'{stars}\nLevel **{self.level}**\nQuantity: **{self.quantity}**x\nGlobally Found: **{self.hero.total}**\n*{self.hero.get_mention()}*\n{"**Upgradable**" if self.quantity >= 3 else ""}'

        return name, value

    def get_info(self):
        """Gets info for inline placement
        
        Returns: str"""
        stars = ''
        if self.hero.stars > 5:
            stars = f'{self.hero.stars}⭐'
        else:
            for _ in range(self.hero.stars):
                stars += '⭐'
        return f'{stars} {self.hero.name}, Level {self.level}, {self.quantity}x'

    def get_save_string(self):
        return f'{self.hero.guild_id}.{self.hero.hero_id}.{self.quantity}.{self.level}'

    @staticmethod
    def from_save_string(bot, string):
        data = string.split('.')
        guild_id = int(data[0])
        hero_id = int(data[1])
        quantity = int(data[2])
        level = int(data[3])
        guild = bot.get_guild(guild_id)
        if guild:
            member = guild.get_member(hero_id)
        else:
            member = None

        hero = Hero(bot, member=member, hero_id=hero_id, guild_id=guild_id)
        
        return Card(bot, hero, quantity, level)


class Deck:
    """A class that handles the specifics of a card.

    Parameters
    ------------
    member: :class:`discord.Member`
        The member the deck relates to.
    guild_id: :class:`int`
        The id number of the guild the deck is in.
    user_id: :class:`int`
        The id number of the member the user relates to.
        """

    cache = {}
    
    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.member = kwargs.get('member')
        if self.member:
            self.guild = self.member.guild
            self.guild_id = self.guild.id
            self.user_id = self.member.id
        else:
            self.guild_id = int(kwargs.get('guild_id'))
            self.user_id = int(kwargs.get('user_id'))
            self.guild = self.bot.get_guild(self.guild_id)
            if self.guild:
                self.member = self.guild.get_member(self.user_id)
            
        self.cards = []
        self.total_points = 0
        self.spent_points = 0

        self.load()

    def add_card(self, card: Card, add_total = True):
        if card.hero.guild_id == self.guild.id:
            add = True
            for c in self.cards:
                if c == card:
                    c += card
                    add = False
            if add:
                self.cards.append(card)
            if add_total:
                card.hero.add_total(1)

    def new(self):
        db.add_deck(self.guild.id, self.member.id)
        self.save()

    def save(self):
        card_saves = []
        for c in self.cards:
            if c.quantity > 0:
                card_saves.append(c.get_save_string())
        card_saves = ','.join(card_saves)
        db.set_deck(
            self.guild_id,
            self.user_id,
            cards = card_saves,
            totalPoints = self.total_points,
            spentPoints = self.spent_points
        )

    def load(self):
        data = db.get_deck(guildID=self.guild_id, userID=self.user_id)
        if data:
            data = data[0]
        else:
            self.new()
            return
        self.cards = []
        card_saves = data['cards'].split(',')
        for s in card_saves:
            if s:
                self.cards.append(Card.from_save_string(self.bot, s))
        self.total_points = int(data['totalPoints'])
        self.spent_points = int(data['spentPoints'])
    
    def get_cards_string(self):
        string = ''
        for c in self.cards:
            stars = ''
            if c.hero.stars > 5:
                stars = f'{c.hero.stars}⭐'
            else:
                for _ in range(c.hero.stars):
                    stars += '⭐'
            string += f'{c.quantity}x | Level **{c.level}** {stars} {c.hero.name}\n'
        return string

    def fill_embed(self, embed: discord.Embed, page = 1, sort = True):
        def sort_function(item):
            return (item.hero.stars, item.level, item.quantity)
        if sort:
            cards = sorted(self.cards, key=sort_function, reverse=True)
        else:
            cards = self.cards
        total_pages = len(cards) // 25 + 1
        if page > total_pages:
            page = total_pages
        starting_index = (page - 1) * 25
        for c in cards[starting_index:starting_index+25]:
            name, value = c.get_embed_info()
            embed.add_field(
                name=name,
                value=value
            )
        embed.set_footer(text=f'Page: {page}/{total_pages}')

    def get_upgradable(self):
        l = []
        for c in self.cards:
            if c.quantity >= 3:
                l.append(c)
        return l

    def add_points(self, points: int):
        self.total_points += points

    def spend_points(self, points: int):
        self.spent_points += points

    def get_current_points(self):
        return self.total_points - self.spent_points

    def get_total_points(self):
        return self.total_points

    @staticmethod
    def db_add_point(bot, member: discord.Member, points: int):
        data = db.get_deck(guildID=member.guild.id, userID=member.id)
        if data:
            data = data[0]
            new_points = int(data['totalPoints']) + points
            db.set_deck(member.guild.id, member.id, totalPoints=new_points)
        else:
            deck = Deck(bot, member=member)
            deck.add_points(points)
            deck.save()

    @staticmethod
    def get_all_in_guild(bot, guild: discord.Guild):
        data = db.get_deck(guildID=guild.id)
        decks = []
        for d in data:
            deck = Deck(bot, guild_id=d['guildID'], user_id=d['userId'])
            decks.append(deck)
        return decks

    @staticmethod
    def update_quantities_from_star_change(bot, guild: discord.Guild, hero: Hero, star_change: int):
        decks = Deck.get_all_in_guild(bot, guild)
        for deck in decks:
            for card in deck.cards:
                if card.hero == hero:
                    if star_change > 0:
                        new_quantity = card.quantity * math.pow(Gacha.RANK_UP_CHANCE, star_change)
                    else:
                        new_quantity = card.quantity * math.pow(numpy.reciprocal(Gacha.RANK_UP_CHANCE) * 0.5, -star_change)
                    new_quantity = math.floor(new_quantity)
                    if new_quantity <= 0:
                        new_quantity = 1
                    change = new_quantity - card.quantity
                    card.quantity = new_quantity
                    deck.save()
                    hero.add_total(change)


class Gacha(commands.Cog):
    POINTS_PER_MINUTE = 1
    POINTS_PER_MESSAGE = 2
    COST_PER_PACK = 50
    RANK_UP_CHANCE = 0.25

    def __init__(self, bot):
        self.bot = bot
        self.started = False
        self.last_message_time = {}
        
    @commands.Cog.listener()
    async def on_ready(self):
        await self.start_up()

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot and not message.content.startswith('-'):
            last_message = self.last_message_time.get(message.author.id, datetime.datetime(2000, 1, 1, 1, 1, 1, 1))
            time_to_check = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
            if last_message <= time_to_check:
                Deck.db_add_point(self.bot, message.author, Gacha.POINTS_PER_MESSAGE)
                self.last_message_time[message.author.id] = datetime.datetime.utcnow()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.bot:
            hero = Hero(self.bot, member=member)
            if hero.fresh:
                hero.active = True
                hero.save()
                embed = discord.Embed(
                    title=f'{hero.name} created with {hero.stars}⭐!',
                    colour=discord.Colour.green(),
                    description='Their card is now available to be found.'
                )
                embed.set_thumbnail(url=hero.member.avatar.url)
                embed.set_footer(text=hero.username)
                if hero.guild.system_channel:
                    await hero.guild.system_channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def deck(self, ctx, page = 1):
        """View your current deck."""
        deck = Deck(self.bot, member=ctx.author)
        embed = discord.Embed(
            title=f'{ctx.author.display_name}\'s Deck',
            colour=discord.Colour.orange()
        )
        deck.fill_embed(embed, page=page)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def add_card(self, ctx, member: discord.Member):
        deck = Deck(self.bot, member=ctx.author)
        card = Card(self.bot, member, 1, 1)
        deck.add_card(card)
        deck.save()

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def refresh_totals(self, ctx):
        db.set_hero(None, None, total=0)
        decks = Deck.get_all_in_guild(self.bot, ctx.guild)
        for deck in decks:
            for c in deck.cards:
                if c.level > 1:
                    c.hero.add_total(c.quantity * ((c.level - 1) * 3))
                else:
                    c.hero.add_total(c.quantity)
        await ctx.send('Refresh Completed')

    @commands.command(aliases=['pack', 'open_pack'])
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.guild_only()
    async def open(self, ctx):
        """Open a new pack of cards."""
        embed = discord.Embed(
            title='Sorry!',
            description='The bot is under going some heavy changes, to maintain the rarity of cards, packs are temporarily unavailable!',
            colour=discord.Colour.red())
        await ctx.send(embed=embed)
        return
        theme = GuildTheme(ctx.guild)
        deck = Deck(self.bot, member=ctx.author)
        cost = Gacha.COST_PER_PACK
        if deck.get_current_points() >= cost:
            embed = discord.Embed(
                title='Opening Pack...',
                colour=discord.Colour.orange()
            )
            await ctx.send(embed=embed, delete_after=3)
            cards_to_get = 4
            new_cards = []
            rarities = []
            weights = []
            gen = numpy.random.default_rng()
            for i in range(len(theme.ranks)):
                rarities.append(i)
                if i > 0:
                    weights.append(math.pow(Gacha.RANK_UP_CHANCE, i))
            s = sum(weights)
            weights.insert(0, 1.0 - s)
            chosen_rarities = gen.choice(rarities, size=cards_to_get, p=weights)

            for i in chosen_rarities:
                if theme.ranks[i].members or i == 0:
                    pool = theme.ranks[i].members
                else:
                    pool = theme.ranks[i-1].members
                member = gen.choice(pool)
                card = Card(self.bot, member, 1, 1)
                deck.add_card(card)
                card.hero.total += 1
                new_cards.append(card)
            deck.spend_points(cost)
            deck.save()
            new_cards = sorted(new_cards, key=lambda x: x.hero.stars)

            await asyncio.sleep(2)

            for card in new_cards:
                name, value = card.get_embed_info()
                embed = discord.Embed(
                    title=name,
                    description=value,
                    colour=theme.ranks[card.hero.stars-1].colour
                )
                embed.set_thumbnail(url=card.hero.member.avatar.url)
                await ctx.send(embed=embed)
                await asyncio.sleep(1)
        else:
            embed = discord.Embed(
                title='Invalid Points',
                colour=discord.Colour.red(),
                description=f'You need **{cost - deck.get_current_points()}** more points.'
            )
            await ctx.send(embed=embed)


    @commands.command()
    @commands.guild_only()
    async def upgrade(self, ctx, *args):
        """Upgrade your cards to the next level.
        
        Keywords
        ------------
        all: Upgrade every upgradable card once."""
        deck = Deck(self.bot, member=ctx.author)
        cards = deck.get_upgradable()
        if 'all' in args:
            overflow = 0
            desc = ''
            for i, old_card in enumerate(cards):
                card = old_card.level_up()
                deck.add_card(card, add_total=False)
                if len(desc) < 1500:
                    desc += f'{card.get_info()}\n'
                else:
                    overflow += 1
            if overflow > 0:
                desc += f'**{overflow}** More...'
            deck.save()
            embed = discord.Embed(
                title='Batch Upgrade Successful',
                description=desc,
                colour=discord.Colour.green()
            )
            await ctx.send(embed=embed)
        else:
            while len(cards) > 0:
                desc = ''
                for i, c in enumerate(cards):
                    if len(desc) < 1500:
                        desc += f'{i}. {c.get_info()}\n'
                    else:
                        desc += f'More...'
                        break
                embed = discord.Embed(
                    title='Upgradable Cards',
                    colour=discord.Colour.orange(),
                    description=desc
                )
                embed.set_footer(text='Respond with the index of the card you want to upgrade.')
                main_message = await ctx.send(embed=embed)
                try:
                    response = await self.bot.wait_for('message', timeout=30.0, check=lambda message: message.author.id == ctx.author.id and message.channel.id == ctx.channel.id)
                    index = int(response.content)
                    old_card = cards[index]
                except (asyncio.TimeoutError, ValueError, IndexError) as e:
                    embed.colour = discord.Colour.dark_grey()
                    embed.set_footer(text=f'{e}')
                    await main_message.edit(embed=embed)
                    return
                await response.delete()

                card = old_card.level_up()
                deck.add_card(card, add_total=False)
                deck.save()

                name, value = card.get_embed_info()
                embed = discord.Embed(
                    title=name,
                    colour=discord.Colour.orange(),
                    description=value
                )
                if card.hero.member:
                    embed.set_thumbnail(url=card.hero.member.avatar.url)
                await main_message.edit(embed=embed)
                cards = deck.get_upgradable()
                await asyncio.sleep(1)
            else:
                embed = discord.Embed(
                    title='No more upgradable cards',
                    colour=discord.Colour.green()
                )
                await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def points(self, ctx):
        """Show your current points."""
        deck = Deck(self.bot, member=ctx.author)
        embed = discord.Embed(
            title=f'{ctx.author.display_name}\'s Points',
            colour=discord.Colour.orange(),
            description=(
                f'Current Points: **{deck.get_current_points()}**\n'
                f'Total Points: **{deck.total_points}**\n\n'
                '__Points Earned Per__\n'
                f'Message: **{Gacha.POINTS_PER_MESSAGE}**\n'
                f'Minute in Voice Channel: **{Gacha.POINTS_PER_MINUTE}**\n\n'
                f'Points per Pack: **{Gacha.COST_PER_PACK}**'
            )
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=['lb'])
    @commands.guild_only()
    async def leaderboard(self, ctx):
        """A leaderboard of total points earned."""
        data = db.get_deck(guildID=ctx.guild.id)
        theme = GuildTheme(ctx.guild)
        embeds: List[discord.Embed] = []
        position = 1
        reversed_ranks = list(reversed(theme.ranks))
        for rank in reversed_ranks:
            if theme.is_bot_only(rank):
                continue
            string = ''
            sorted_decks = sorted([Deck(self.bot, member=x) for x in rank.members], key=lambda x: x.total_points, reverse=True)
            for deck in sorted_decks[:5]:
                if deck.member == ctx.author:
                    string += f'**{position}. {deck.member.mention}: {deck.total_points} Points**\n'
                else:
                    string += f'{position}. {deck.member.mention}: {deck.total_points} Points\n'
                position += 1
            embed = discord.Embed(
                title=f'{rank.name}',
                colour=rank.role.colour,
                description=string)
            embeds.append(embed)
        await ctx.send(embeds=embeds[:10])
        return
        sorted_data = sorted(data, key=lambda x: int(x['totalPoints']), reverse=True)
        string = ''
        for i, d in enumerate(sorted_data[:10], start=1):
            m = ctx.guild.get_member(int(d['userID']))
            if m:
                if m == ctx.author:
                    string += f'**{i}. {m.mention}: {d["totalPoints"]:,d} Points**\n'
                else:
                    string += f'{i}. {m.mention}: {d["totalPoints"]:,d} Points\n'
            else:
                string += f'{i}. invalid-user: {d["totalPoints"]:,d} Points\n'
        if ctx.author.id not in (int(d['userID']) for d in sorted_data[:10]):
            index = list(int(d['userID']) for d in sorted_data).index(ctx.author.id)
            string += f'\n**{index + 1}. {ctx.author.mention}: {sorted_data[index]["totalPoints"]:,d} Points**'
        embed = discord.Embed(
            title='Total Points Leaderboard',
            colour=discord.Colour.orange(),
            description=string
        )
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.command()
    @commands.guild_only()
    async def rarest(self, ctx):
        """Get the top 10 rarest cards."""
        heroes = Hero.list_from_guild(self.bot, ctx.guild)
        filtered_heroes = filter(lambda x: x.stars > 1, heroes)
        sorted_heroes = sorted(filtered_heroes, key=lambda x: x.total)
        string = ''
        if len(sorted_heroes) > 10:
            iterable = sorted_heroes[:9]
        else:
            iterable = sorted_heroes
        
        for i, hero in enumerate(iterable, start=1):
            string += f'{i}.. **{hero.stars}**⭐ {hero.get_mention()}: **{hero.total}** Owned\n'
                
        embed = discord.Embed(
            title='Rarest Cards',
            description=string,
            colour=discord.Colour.orange()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def chances(self, ctx):
        """Show current chances to get specific cards."""
        theme = GuildTheme(ctx.guild)
        chances = ''

        weights = []
        for i in range(len(theme.ranks)):
            if i > 0:
                weights.append(math.pow(Gacha.RANK_UP_CHANCE, i))
        s = sum(weights)
        weights.insert(0, 1.0 - s)

        for i, chance in enumerate(weights):
            try:
                chance_to_get_user = chance * (1 / len(theme.ranks[i].members))
            except ZeroDivisionError:
                chance_to_get_user = 0.0
            chances += f'Chance to get {i+1}⭐: {chance:02.2%}. To get specific user: {chance_to_get_user:02.2%}\n'
        embed = discord.Embed(
            title='Draw chances',
            description=chances,
            colour=discord.Colour.orange()
        )
        await ctx.send(embed=embed)

    @tasks.loop(minutes=2)
    async def voice_points(self):
        for guild in self.bot.guilds:
            for voice in guild.voice_channels:
                if voice != guild.afk_channel:
                    for member in voice.members:
                        if not member.bot:
                            if len(voice.members) > 1:
                                Deck.db_add_point(self.bot, member, Gacha.POINTS_PER_MINUTE * 2)
                            else:
                                Deck.db_add_point(self.bot, member, Gacha.POINTS_PER_MINUTE * 2 // 2)

    @tasks.loop(minutes=30)
    async def hero_check(self):
        heroes = Hero.list_all(self.bot)
        for hero in heroes:
            old = hero.stars
            if hero.member and not hero.active:
                embed = discord.Embed(
                    title=f'{hero.name} activated!',
                    colour=discord.Colour.green(),
                    description='Their card is now available to be found.'
                )
                embed.set_thumbnail(url=hero.member.avatar.url)
                embed.set_footer(text=hero.username)
                hero.active = True
                hero.save()
                if hero.guild.system_channel:
                    await hero.guild.system_channel.send(embed=embed)
            elif not hero.member and hero.active:
                embed = discord.Embed(
                    title=f'{hero.name} deactivated!',
                    colour=discord.Colour.red(),
                    description='Their card is no longer available to be found.'
                )
                embed.set_footer(text=hero.username)
                hero.active = False
                hero.save()
                if hero.guild and hero.guild.system_channel:
                    await hero.guild.system_channel.send(embed=embed)

            if hero.member and hero.check_stars():
                hero.save()
                difference = hero.stars - old
                Deck.update_quantities_from_star_change(self.bot, hero.guild, hero, difference)
                change = 'upgraded' if hero.stars > old else 'downgraded'
                embed = discord.Embed(
                    title=f'{hero.name} {change} to {hero.stars} stars!',
                    colour=discord.Colour.orange()
                )
                embed.set_thumbnail(url=hero.member.avatar.url)
                embed.set_footer(text='Card quantities affected accordingly.')
                if hero.guild.system_channel:
                    await hero.guild.system_channel.send(embed=embed)

    @tasks.loop(minutes=30)
    async def competitive_ranks(self):
        guilds = self.bot.guilds
        for guild in guilds:
            theme = GuildTheme(guild)
            sorted_ranks = reversed(theme.ranks)
            filled_ranks = []
            zeros = 0
            for rank in sorted_ranks:
                if theme.is_bot_only(rank):
                    continue
                if rank.max_members == 0:
                    zeros += 1
                filled_ranks += [rank for _ in range(rank.max_members)]
            if zeros > 1:
                print(f'{guild.name} has more than 1 zero max ranks.')
                continue
            print([x.name for x in filled_ranks])
            decks = Deck.get_all_in_guild(self.bot, guild)
            sorted_decks = sorted(decks, key=lambda x: x.get_total_points(), reverse=True)
            for i, deck in enumerate(sorted_decks):
                if deck.member.bot:
                    continue
                if i > len(filled_ranks) - 1:
                    await theme.set_member_rank(deck.member, theme.ranks[0].role)
                else:
                    await theme.set_member_rank(deck.member, filled_ranks[i].role)

    async def start_up(self):
        if self.started:
            return
        self.started = True
        new_heroes = []
        for guild in self.bot.guilds:
            for member in guild.members:
                hero = Hero(self.bot, member=member)
                if hero.fresh:
                    new_heroes.append(hero)
                    hero.active = True
                    hero.save()
        
        if len(new_heroes) > 3:
            string = ''
            if len(new_heroes) > 20:
                for h in new_heroes[:19]:
                    string += f'{h.name} {h.get_stars_string()}\n'
                string += f'**{len(new_heroes) - 20}** More...'
            else:
                for h in new_heroes:
                    string += f'{h.name} {h.get_stars_string()}\n'
            embed = discord.Embed(
                title=f'{len(new_heroes)} new heroes created!',
                colour=discord.Colour.green(),
                description=string
            )
            if h.guild.system_channel:
                await h.guild.system_channel.send(embed=embed)
        else:
            for h in new_heroes:
                embed = discord.Embed(
                    title=f'{h.name} created with {h.get_stars_string()}!',
                    colour=discord.Colour.green(),
                    description='Their card is now available to be found.'
                )
                embed.set_thumbnail(url=h.member.avatar.url)
                embed.set_footer(text=h.username)
                if h.guild.system_channel:
                    await h.guild.system_channel.send(embed=embed)
        self.competitive_ranks.start()
        self.hero_check.start()
        self.voice_points.start()

def setup(bot):
    bot.add_cog(Gacha(bot))