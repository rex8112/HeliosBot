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
import discord
from discord import app_commands
from discord.ext import commands
from typing_extensions import Literal

from helios import Blackjack, Items
from helios.shop import *

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember
    from helios.items import MuteItem


@app_commands.guild_only()
class InventoryCog(commands.GroupCog, name='inventory'):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

        self.temp_mute_context = app_commands.ContextMenu(
            name='Temp Mute',
            callback=self.temp_mute
        )

        self.bot.tree.add_command(self.temp_mute_context)

    @app_commands.command(name='show', description='Show your inventory')
    async def show_inventory(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        if member is None or member.inventory is None:
            return await interaction.response.send_message('You do not have an inventory.', ephemeral=True)
        await interaction.response.send_message(embed=member.inventory.get_embed(), ephemeral=True)

    async def temp_mute(self, interaction: discord.Interaction, member: discord.Member):
        server = self.bot.servers.get(interaction.guild_id)
        author = server.members.get(interaction.user.id)
        member = server.members.get(member.id)
        items = author.inventory.get_items('mute_token')
        item: Optional['MuteItem'] = items[0] if len(items) > 0 else None
        if item is None:
            return await interaction.response.send_message(f'{author.member.mention}\nYou do not have a mute token.', ephemeral=True)
        verify, error = await item.verify(author, member, 1)
        if not verify:
            return await interaction.response.send_message(f'{author.member.mention}\n{error}', ephemeral=True)
        await item.use(author, member, 1)
        await interaction.response.send_message(f'{author.member.mention}\nPurchased.', ephemeral=True)


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(InventoryCog(bot))
