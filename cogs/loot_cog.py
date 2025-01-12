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
import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from typing_extensions import Literal

from helios import Blackjack, Items
from helios.shop import *
from helios.loot_pools import Pools

if TYPE_CHECKING:
    from helios import HeliosBot, HeliosMember


@app_commands.guild_only()
class LootCog(commands.GroupCog, name='lootcrate'):
    def __init__(self, bot: 'HeliosBot'):
        self.bot = bot

    @app_commands.command(name='open', description='Open a lootcrate')
    async def open_lootcrate(self, interaction: discord.Interaction):
        server = self.bot.servers.get(interaction.guild_id)
        member = server.members.get(interaction.user.id)
        loot_crates = member.inventory.get_items('loot_crate')
        if not loot_crates:
            await interaction.response.send_message('You do not have any loot crates to open', ephemeral=True)
            return
        await interaction.response.send_message('Opening loot crate...')
        loot_crate = loot_crates[0]
        await member.inventory.remove_item(loot_crate)
        pool = Pools[loot_crate.data['type']]()
        items = pool.get_random_items(3)
        [await member.inventory.add_item(i.item, i.item.quantity) for i in items]
        embeds = [
            discord.Embed(
                description=f'**{item.item.display_name}** x{item.item.quantity}\n{item.item.get_description()}',
                color=item.color
            ) for item in items
        ]
        for i in range(len(embeds)):
            await asyncio.sleep(1)
            await interaction.edit_original_response(embeds=embeds[:i + 1])


async def setup(bot: 'HeliosBot'):
    await bot.add_cog(LootCog(bot))
