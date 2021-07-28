import asyncio
import discord

from discord.ext import tasks, commands

from tools.database import db

class GuildTheme:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.loaded = False
        if self.load():
            self.loaded = True
        else:
            self.new()

    def load(self):
        data = db.get_theme(guildID=self.guild.id)
        if len(data) > 0:
            data = data[0]
        else:
            return False
        
        self.theme_name = data['themeName']
        self.guild_name = data['guildName']
        self.ranks = []
        raw_ranks = data['ranks']
        if raw_ranks:
            ranks = [int(x) for x in raw_ranks.split(',')]
            for r in ranks:
                rank = self.guild.get_role(r)
                self.ranks.append(rank)
        else:
            self.ranks = []
        return True

    def save(self):
        ranks = ','.join(str(x.id) for x in self.ranks)
        db.set_theme(
            self.guild.id,
            themeName = self.theme_name,
            guildName = self.guild.name,
            ranks = ranks
        )

    def new(self):
        db.add_theme(self.guild.id, self.guild.name)
        self.theme_name = 'Nothing'
        self.guild_name = self.guild.name
        self.ranks = []

    def add_rank(self, role: discord.Role, index=-1):
        if index > -1:
            self.ranks.insert(index, role)
        else:
            self.ranks.append(role)

    def del_rank(self, index: int):
        return self.ranks.pop(index)

    def get_current_rank_index(self, member: discord.Member):
        r = member.roles
        for i, rank in enumerate(self.ranks):
            if rank in r:
                return i

    def is_bot_only(self, rank: discord.Role) -> bool:
        bot_only = True
        for member in rank.members:
            if not member.bot:
                bot_only = False
        return bot_only


class Theme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def add_rank(self, ctx, role: discord.Role, index=-1):
        theme = GuildTheme(ctx.guild)
        theme.add_rank(role, index)
        theme.save()
        
        embed = discord.Embed(
            title=f'{role} added succesfully!',
            colour=discord.Colour.green()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def del_rank(self, ctx, index):
        theme = GuildTheme(ctx.guild)
        index = int(index)
        role = theme.del_rank(index)
        theme.save()

        for m in role.members:
            if index > 0:
                await m.add_roles(theme.ranks[index-1])
            else:
                await m.add_roles(theme.ranks[index])
        
        embed = discord.Embed(
            title=f'{role} removed succesfully!',
            colour=discord.Colour.green()
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def ranks(self, ctx):
        theme = GuildTheme(ctx.guild)
        ranks_string = ''
        for i, r in enumerate(theme.ranks):
            ranks_string += f'{i}. {r}: {len(r.members):02} Members\n'

        embed = discord.Embed(
            title='All Ranks',
            colour=discord.Colour.blue(),
            description=ranks_string
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def promote(self, ctx, member: discord.Member, amount = 1):
        theme = GuildTheme(ctx.guild)
        author = theme.get_current_rank_index(ctx.author)
        mem = theme.get_current_rank_index(member)

        if author > mem + amount or ctx.author.guild_permissions.administrator:
            if mem < len(theme.ranks) - amount:
                if theme.is_bot_only(theme.ranks[mem+amount]):
                    embed = discord.Embed(
                        title='This rank is bot only!',
                        colour=discord.Colour.red(),
                    )
                else:
                    await member.add_roles(theme.ranks[mem+amount])
                    await member.remove_roles(theme.ranks[mem])

                    embed = discord.Embed(
                        title=f'{member.display_name} promoted to {theme.ranks[mem+amount]}',
                        colour=discord.Colour.green()
                    )
            else:
                embed = discord.Embed(
                    title='Already max rank',
                    colour=discord.Colour.red()
                )
        else:
            embed = discord.Embed(
                title='Invalid permissions to promote rank',
                colour=discord.Colour.red()
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def demote(self, ctx, member: discord.Member, amount = 1):
        theme = GuildTheme(ctx.guild)
        author = theme.get_current_rank_index(ctx.author)
        mem = theme.get_current_rank_index(member)

        if author > mem or ctx.author.guild_permissions.administrator:
            if mem > 0:
                await member.add_roles(theme.ranks[mem-amount])
                await member.remove_roles(theme.ranks[mem])

                embed = discord.Embed(
                    title=f'{member.display_name} demoted to {theme.ranks[mem-amount]}',
                    colour=discord.Colour.green()
                )
            else:
                embed = discord.Embed(
                    title='Already minimum rank',
                    colour=discord.Colour.red()
                )
        else:
            embed = discord.Embed(
                title='Invalid permissions to demote rank',
                colour=discord.Colour.red()
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def change_theme(self, ctx):
        theme = GuildTheme(ctx.guild)

        template_embed = discord.Embed(
            title='Theme Change',
            colour=discord.Colour.orange()
        )

        name_embed = template_embed.copy()
        name_embed.description = 'What is the name of the new theme?'
        main_message = await ctx.send(embed=name_embed)
        try:
            response = await self.bot.wait_for('message', timeout=30.0, check=lambda message: message.author.id == ctx.author.id and message.channel.id == ctx.channel.id)
        except asyncio.TimeoutError:
            await main_message.edit(embed=template_embed)
            return
        theme.theme_name = response.content
        
        name_embed.description = 'What is the new name of the server?'
        await main_message.edit(embed=name_embed)
        try:
            response = await self.bot.wait_for('message', timeout=30.0, check=lambda message: message.author.id == ctx.author.id and message.channel.id == ctx.channel.id)
        except asyncio.TimeoutError:
            await main_message.edit(embed=template_embed)
            return
        theme.guild_name = response.content

        new_ranks = []
        for rank in theme.ranks:
            name_embed.description = f'What is the new name for the rank: {rank} ?'
            await main_message.edit(embed=name_embed)
            try:
                response = await self.bot.wait_for('message', timeout=30.0, check=lambda message: message.author.id == ctx.author.id and message.channel.id == ctx.channel.id)
            except asyncio.TimeoutError:
                await main_message.edit(embed=template_embed)
                return
            new_ranks.append(response.content)

        await theme.guild.edit(name=theme.guild_name)
        for i, r in enumerate(theme.ranks):
            await r.edit(name=new_ranks[i])
        theme.save()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        theme = GuildTheme(member.guild)
        if theme.ranks:
            await member.add_roles(theme.ranks[0])

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            theme = GuildTheme(guild)
            if guild.name != theme.guild_name:
                theme.guild_name = guild.name
                theme.save()
            if theme.ranks:
                for m in guild.members:
                    if theme.get_current_rank_index(m) == None:
                        await m.add_roles(theme.ranks[0])


def setup(bot):
    bot.add_cog(Theme(bot))