import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import MISSING

from helios.horses.auction import GroupAuction
from helios.horses.views import HorseOwnerView

if TYPE_CHECKING:
    from helios import HeliosBot


class StadiumCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='points', description='See your current points')
    @app_commands.guild_only()
    async def points(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        await interaction.response.send_message(
            f'Current Points: **{member.points:,}**\nActivity Points: **{member.activity_points:,}**',
            ephemeral=True
        )

    @app_commands.command(name='daily', description='Claim daily points')
    @app_commands.guild_only()
    async def daily(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        if member.claim_daily():
            await interaction.response.defer(ephemeral=True)
            await member.save()
            await interaction.followup.send(f'Claimed **{server.stadium.daily_points:,}** points!')
        else:
            epoch_time = server.stadium.epoch_day.time()
            tomorrow = datetime.now().astimezone() + timedelta(days=1)
            tomorrow = tomorrow.date()
            tomorrow = datetime.combine(tomorrow, epoch_time)
            await interaction.response.send_message(f'Check back <t:{int(tomorrow.timestamp())}:R>', ephemeral=True)

    @app_commands.command(name='horses', description='Show current horses.')
    @app_commands.guild_only()
    async def horses(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        horses = member.horses
        horses_str = ''
        for horse in horses.values():
            horses_str += f'{horse.name}\n'
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title='Current Horses',
            description=horses_str
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='inspect', description='Inspect Horse.')
    @app_commands.guild_only()
    async def inspect(self, interaction: discord.Interaction, horse_name: str):
        server = self.bot.servers.get(interaction.guild_id)
        horse = server.stadium.get_horse_name(horse_name)
        if horse:
            owner_id = (horse.owner.member.id
                        if horse.owner else horse.stadium.owner.id)
            owner = owner_id == interaction.user.id
            embeds = horse.get_inspect_embeds(is_owner=owner)
            view = HorseOwnerView(horse.owner, horse) if owner else MISSING
            await interaction.response.send_message(embeds=embeds,
                                                    ephemeral=True,
                                                    view=view)
        else:
            await interaction.response.send_message('Horse not found',
                                                    ephemeral=True)

    @app_commands.command(name='like',
                          description=('Like a horse, making it more likely '
                                       'to show up in auctions.'))
    @app_commands.guild_only()
    async def like(self, interaction: discord.Interaction, horse_name: str):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        horse = server.stadium.get_horse_name(horse_name)
        if horse:
            if horse.owner is not None:
                await interaction.response.send_message(
                    (f'This horse is already owned by <@{horse.owner.id}>, '
                     f'so liking it has zero effect.'),
                    ephemeral=True
                )
                return

            if member.settings['day_liked'] == server.stadium.day:
                await interaction.response.send_message(
                    ('You have already liked a horse today, try again '
                     'tomorrow!'),
                    ephemeral=True
                )
            else:
                member.settings['day_liked'] = server.stadium.day
                horse.likes += 1
                await horse.save()
                await member.save(force=True)
                await interaction.response.send_message(
                    f'Successfully liked **{horse.name}**',
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f'**{horse_name}** does not exist!',
                ephemeral=True
            )

    @app_commands.command(name='test_group_auction')
    @app_commands.guilds(466060673651310593)
    async def test_group_auction(self, interaction: discord.Interaction,
                                 seconds: int):
        server = self.bot.servers.get(interaction.guild_id)
        a = GroupAuction(server.stadium.auction_house, interaction.channel)
        a.settings['duration'] = seconds
        a.settings['start_time'] = datetime.now().astimezone().isoformat()
        horses = random.sample(list(server.stadium.horses.values()), 10)
        a.create_listings(horses)
        server.stadium.auction_house.auctions.append(a)
        await interaction.response.send_message('Auction Created',
                                                ephemeral=True)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(StadiumCog(bot))
