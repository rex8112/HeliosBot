#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt

from helios import Colour, ViolationView, PaginatorSelectView

if TYPE_CHECKING:
    from helios import HeliosBot, Violation


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
        v_titles = [str(v) for v in violations]
        view = PaginatorSelectView(violations, v_titles, build_violations_embeds)
        await interaction.response.send_message(embeds=build_violations_embeds(view.get_paged_values()), view=view,
                                                ephemeral=True)
        if await view.wait():
            return
        selected: 'Violation' = view.selected
        await interaction.edit_original_response(embed=selected.get_info_embed(),
                                                 view=ViolationView(server, selected.id))


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(CourtCog(bot))
