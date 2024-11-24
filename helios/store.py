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
import datetime
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

from .items import Items
from .colour import Colour
from .database import StoreModel
from .items import StoreItem

if TYPE_CHECKING:
    from .member import HeliosMember
    from .helios_bot import HeliosBot
    from .server import Server

class Store:
    def __init__(self, server:  'Server'):
        self.server = server
        self.items: list['StoreItem'] = []
        self.next_refresh = datetime.datetime.now(datetime.timezone.utc)

        self.db_entry = None

    def to_dict(self):
        return {
            'items': [item.to_dict() for item in self.items],
            'next_refresh': self.next_refresh,
        }

    @classmethod
    def from_dict(cls, server: 'Server', data: dict):
        store = cls(server)
        for item_data in data['items']:
            store.add_item(StoreItem.from_dict(item_data))
        store.next_refresh = data['next_refresh']
        return store

    @classmethod
    def from_db(cls, server: 'Server', entry: StoreModel):
        store = cls(server)
        for item_data in entry.items:
            store.add_item(StoreItem.from_dict(item_data))
        store.next_refresh = entry.next_refresh
        store.db_entry = entry
        return store

    @classmethod
    async def from_server(cls, server: 'Server'):
        entry = await StoreModel.get(server=server.db_entry)
        if entry is None:
            store = cls(server)
            await store.reset()
        else:
            store = cls.from_db(server, entry)
        return store

    async def save(self):
        if self.db_entry is None:
            self.db_entry = await StoreModel.create(
                server=self.server.db_entry,
                items=[item.to_dict() for item in self.items],
                next_refresh=self.next_refresh,
            )
        else:
            await self.db_entry.async_update(**self.to_dict())

    def start(self):
        self.refresh_loop.start()

    def stop(self):
        self.refresh_loop.stop()

    @tasks.loop(minutes=1)
    async def refresh_loop(self):
        if self.next_refresh < datetime.datetime.now(datetime.timezone.utc):
            await self.refresh()

    async def refresh(self):
        for item in self.items:
            stock_increment = (item.max_stock - item.min_stock) // 5
            price_increment = (item.max_price - item.min_price) // 5
            diff = item.stock -  item.quantity
            half = item.stock // 2
            perc = diff / half # 1.0 = 50% stock remaining, 1.5 = 25% stock remaining, 2.0 = 0% stock remaining, 0.5 = 75% stock remaining, etc.
            if perc < 1.0:
                inverted = 1.0 - perc
                s_inc = max(int(stock_increment * inverted), 1)
                p_inc = max(int(price_increment * inverted), 1)
                item.stock -= s_inc
                item.price -= p_inc
            elif perc > 1.0:
                inverted = perc - 1.0
                s_inc = max(int(stock_increment * inverted), 1)
                p_inc = max(int(price_increment * inverted), 1)
                item.stock += s_inc
                item.price += p_inc
            item.quantity = item.stock
        self.set_next_refresh()
        await self.save()

    def set_next_refresh(self):
        """Set the next refresh time based on the server settings"""
        refreshes = self.server.settings['daily_store_refreshes']
        midnight = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        interval = (24 * 60 * 60) / refreshes
        all_refreshes = [midnight + datetime.timedelta(seconds=interval * i) for i in range(refreshes)]
        for refresh in all_refreshes:
            if refresh > datetime.datetime.now(datetime.timezone.utc):
                self.next_refresh = refresh
                return
        self.next_refresh = all_refreshes[0] + datetime.timedelta(days=1)

    @staticmethod
    def get_reset_items():
        return [
            StoreItem.from_item(Items.mute_token(), 100, 1000, 50, 5, 15,  3),
            StoreItem.from_item(Items.deafen_token(), 100, 1000, 50, 5, 15,  3),
            StoreItem.from_item(Items.shield(), 100, 500, 10, 10, 30,  5),
            StoreItem.from_item(Items.bubble(), 1000, 10_000, 1000, 5, 10,  1),
            StoreItem.from_item(Items.deflector(), 500, 10_000, 500, 5, 10,  1),
        ]

    async def reset(self):
        self.items = self.get_reset_items()
        for item in self.items:
            item.set_to_max()
            item.refresh()
        self.set_next_refresh()
        await self.save()

    async def purchase(self, item: StoreItem, member: 'HeliosMember', quantity: int):
        quantity = min(quantity, item.quantity)
        if quantity <= 0:
            return 0
        total_price = item.price * quantity
        if member.points < total_price:
            return 0
        item.quantity -= quantity
        await member.add_points(-total_price, 'Helios: Store', f'Purchased {quantity} of {item.name}')
        await member.inventory.add_item(item.to_item(), quantity)
        await self.save()
        return quantity

    def add_item(self, item: 'StoreItem'):
        self.items.append(item)

    def remove_item(self, item: 'StoreItem'):
        self.items.remove(item)

    def get_view(self):
        return StoreView(self.server.bot)

    def get_embed(self):
        embed = discord.Embed(
            title=f'{self.server.name} Store',
            description='Here are the items available in the store:\n'
                        f'Next Refresh {discord.utils.format_dt(self.next_refresh, "R")}',
            colour=Colour.store()
        )
        for item in self.items:
            embed.add_field(
                name=item.display_name,
                value=f'Price: **{item.price:,}**\nStock: **{item.quantity:,}**',
                inline=True
            )
        return embed

    def get_edit_view(self):
        ...


class StoreView(discord.ui.View):
    """A view with a button to bring up the StoreSelectView"""
    def __init__(self, bot: 'HeliosBot'):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='Select Item', custom_id='helios:store:select')
    async def show_select(self, interaction: discord.Interaction, button: discord.ui.Button):
        server = self.bot.servers.get(interaction.guild.id)
        view = StoreSelectView(server.store)
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label='🔃', custom_id='helios:store:refresh')
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        server = self.bot.servers.get(interaction.guild.id)
        store = server.store
        await interaction.response.edit_message(embed=store.get_embed(), view=self)


class StoreSelectView(discord.ui.View):
    def __init__(self, store: Store):
        super().__init__(timeout=180)
        self.store = store
        self.refresh_select()

    def refresh_select(self):
        self.select_item.options = [
            discord.SelectOption(
                label=item.display_name,
                value=str(i),
                description=f'Remaining Stock: {item.quantity}')
            for i, item in enumerate(self.store.items)]

    @discord.ui.select(placeholder='Select an item to buy', options=[])
    async def select_item(self, interaction: discord.Interaction, select: discord.ui.Select):
        member = self.store.server.members.get(interaction.user.id)
        item = self.store.items[int(select.values[0])]
        view = PurchaseView(item, member)
        await interaction.response.edit_message(view=view, embed=view.get_embed())


class PurchaseView(discord.ui.View):
    def __init__(self, item: StoreItem, author: 'HeliosMember'):
        super().__init__(timeout=180)
        self.author = author
        self.store = author.server.store
        self.item = item
        self.selected_quantity = 1
        self.update_buttons()

    def update_buttons(self):
        self.quantity_label.label = f"{self.selected_quantity}"
        self.increase.disabled = self.selected_quantity >= self.item.quantity
        self.decrease.disabled = self.selected_quantity <= 1

    def get_embed(self):
        embed = discord.Embed(title=f"Item: {self.item.display_name}",
                              description="Here are the details of the selected item:")
        embed.add_field(name="Price", value=f'{self.item.price * self.selected_quantity:,}', inline=False)
        embed.add_field(name="Remaining Stock", value=str(self.item.quantity), inline=False)
        return embed

    @discord.ui.button(label='Purchase', style=discord.ButtonStyle.success, row=1)
    async def purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if 0 < self.selected_quantity <= self.item.quantity:
            self.stop()
            bought = await self.store.purchase(self.item, self.author, self.selected_quantity)
            await interaction.response.edit_message(
                content=f'You bought {bought} {self.item.display_name}.', view=None, embed=None)
        else:
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content='Purchase canceled.', view=None, embed=None)
        self.stop()

    @discord.ui.button(label='-', style=discord.ButtonStyle.grey, row=0)
    async def decrease(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_quantity > 1:
            self.selected_quantity -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label='1', style=discord.ButtonStyle.grey, disabled=True, row=0)
    async def quantity_label(self, interaction: discord.Interaction, button: discord.ui.Button):
        ...  # This button is just to display the selected quantity and won't have any interaction.

    @discord.ui.button(label='+', style=discord.ButtonStyle.grey, row=0)
    async def increase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_quantity < self.item.quantity:
            self.selected_quantity += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
