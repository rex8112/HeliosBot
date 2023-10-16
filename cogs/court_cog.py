from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt

from helios import Colour, ViolationView
from helios.tools import PaginatorSelectView

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember, Violation


def build_violations_embeds(violations: list['Violation']):
    embed = discord.Embed(
        title='Violations',
        colour=Colour.violation()
    )
    for v in violations:
        s = ''
        if v.paid:
            s = f'**Paid**\n{v.description}'
        else:
            s = f'**Due: {format_dt(v.due_date)}**\n{v.description}'

        embed.add_field(
            name=f'{v.type.name.capitalize()} Violation #{v.id}',
            value=s,
            inline=False
        )
    return [embed]


class CourtCog(commands.Cog):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='violations', description='See your current violations')
    @app_commands.guild_only()
    async def violations(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        violations = await server.court.get_violations(member)
        v_dict: dict['Violation', str] = {}
        for violation in violations:
            v_dict[violation] = str(violation)
        view = PaginatorSelectView(v_dict, build_violations_embeds)
        await interaction.response.send_message(embeds=build_violations_embeds(view.get_paged_values()), view=view,
                                                ephemeral=True)
        if await view.wait():
            return
        selected: 'Violation' = view.selected
        await interaction.edit_original_response(embed=selected.get_info_embed(),
                                                 view=ViolationView(server, selected.id))


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(CourtCog(bot))
