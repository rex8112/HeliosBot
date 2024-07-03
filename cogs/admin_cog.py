#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
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

from discord import app_commands
from discord.ext import commands

from helios.shop import *

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember


@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
class AdminCog(commands.GroupCog, name='admin'):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='change_points', description='See your current points')
    @commands.has_permissions(administrator=True)
    @app_commands.describe(target='Member to change points for',
                           points='Amount of points to add or remove, supports negative numbers',
                           description='Reason for changing points',
                           announce='Whether to announce the change to the target')
    async def points(self, interaction: discord.Interaction, target: discord.Member, points: int, description: str = '',
                     announce: bool = False):
        server = self.bot.servers.get(interaction.guild_id)
        target_member = server.members.get(target.id)
        await target_member.add_points(points, 'Helios', f'ADMIN {interaction.user.name[:10]}: {description}')
        await target_member.save()
        await interaction.response.send_message(
            f'Added {points} points to {target.display_name}',
            ephemeral=True
        )

        if announce:
            embed = discord.Embed(
                title=f'{server.points_name.capitalize()} Changed',
                description=f'Your {server.points_name} have been changed by **{points}** by an admin. You now have '
                            f'**{target_member.points}** {server.points_name.capitalize()}\n\nReason: {description}',
                color=discord.Color.red()
            )
            try:
                await target.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(AdminCog(bot))
