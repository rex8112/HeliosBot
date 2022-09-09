import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

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
            tomorrow = datetime.datetime.now().astimezone() + datetime.timedelta(days=1)
            tomorrow = tomorrow.date()
            tomorrow = datetime.datetime.combine(tomorrow, epoch_time)
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
            info = f'Owner: <@{owner_id}>\n'
            if owner_id == interaction.user.id:
                results = server.stadium.get_win_place_show_loss(horse.records)
                info += (f'Record: {results[0]}W/{results[1]}P/'
                         f'{results[2]}S/{results[3]}/L\n')
            else:
                win, loss = server.stadium.get_win_loss(horse.records)
                info += f'Record: {win}W/{loss}L\n'
            info += (f'Breed: {horse.breed.name}\n'
                     f'Gender: {horse.gender}\n'
                     f'Age: {horse.age}')
            embeds = []
            embed = discord.Embed(
                colour=discord.Colour.orange(),
                title=horse.name,
                description=info
            )
            embeds.append(embed)
            if horse.get_flag('DELETE'):
                embed2 = discord.Embed(
                    colour=discord.Colour.red(),
                    title='PENDING DELETION',
                    description=('This horse is being prepared to be '
                                 '"let go." If you believe this is in error '
                                 'please contact rex8112#1200 immediately as '
                                 'the horse has limited time remaining.')
                )
                embeds.append(embed2)
            await interaction.response.send_message(embeds=embeds,
                                                    ephemeral=True)
        else:
            await interaction.response.send_message('Horse not found',
                                                    ephemeral=True)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(StadiumCog(bot))
