#  MIT License
#
#  Copyright (c) 2025 Riley Winkler
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
import random
from typing import TYPE_CHECKING, Type

import discord
from discord import Colour
from enum import Enum

from .items import Items

if TYPE_CHECKING:
    from .items import Item


class LootRarities(Enum):
    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    EPIC = 4
    LEGENDARY = 5

def loot_rarity_name(rarity: LootRarities):
    if rarity == LootRarities.COMMON:
        return "Common"
    elif rarity == LootRarities.UNCOMMON:
        return "Uncommon"
    elif rarity == LootRarities.RARE:
        return "Rare"
    elif rarity == LootRarities.EPIC:
        return "Epic"
    elif rarity == LootRarities.LEGENDARY:
        return "Legendary"
    else:
        return "Unknown"

def loot_rarity_color(rarity: LootRarities):
    if rarity == LootRarities.COMMON:
        return Colour.from_str('#bfbfbf')
    elif rarity == LootRarities.UNCOMMON:
        return Colour.from_str('#00FF00')
    elif rarity == LootRarities.RARE:
        return Colour.from_str('#0000FF')
    elif rarity == LootRarities.EPIC:
        return Colour.from_str('#FF00FF')
    elif rarity == LootRarities.LEGENDARY:
        return Colour.from_str('#cc9900')
    else:
        return 0xFFFFFF

class LootItem:
    def __init__(self, item: 'Item', rarity: LootRarities, quantity: int = 1):
        self.item = item
        self.item.quantity = quantity
        self.rarity = rarity
        self.name = item.name
        self.description = item.get_description()
        self.color = loot_rarity_color(rarity)
        self.rarity_name = loot_rarity_name(rarity)

    def __repr__(self):
        return f"<LootItem({self.rarity_name} {self.name} x{self.item.quantity})>"

    def get_item(self):
        return self.item.copy()


class LootPool:
    """A pool of items that can be randomly selected from."""
    ITEMS = []
    def __init__(self):
        self.common_chance = 0.0
        self.items, self.weights = self.build_weighted_pool()

    def get_random_items(self, count: int = 1) -> list[LootItem]:
        """Get a random item from the pool."""
        return random.choices(self.items, weights=self.weights, k=count)

    def get_loot_pool_embeds(self):
        embeds = []
        rarity_items = {rarity: [] for rarity in LootRarities}
        for item in self.ITEMS:
            rarity_items[item.rarity].append(item)

        for rarity, items in rarity_items.items():
            if items:
                embed = discord.Embed(
                    title=f'{loot_rarity_name(rarity)} Items {self.get_loot_rarity_chance(rarity):.1%}',
                    description='\n'.join([f'__**{item.item.display_name} x{item.item.quantity}**__\n{item.item.get_description()}' for item in items]),
                    colour=loot_rarity_color(rarity).value
                )
                embeds.append(embed)
        return embeds

    def get_loot_rarity_chance(self, rarity: LootRarities):
        """Get the chance of getting a certain rarity."""
        if rarity == LootRarities.COMMON:
            return self.common_chance
        elif rarity == LootRarities.UNCOMMON:
            return 0.20
        elif rarity == LootRarities.RARE:
            return 0.10
        elif rarity == LootRarities.EPIC:
            return 0.05
        elif rarity == LootRarities.LEGENDARY:
            return 0.006
        else:
            return 0.0

    def build_weighted_pool(self) -> tuple[list[LootItem], list[float]]:
        """Builds a weighted pool of items based on their rarity."""
        # Count the number of items in each rarity
        rarity_counts = {rarity: 0 for rarity in LootRarities}
        for item in self.ITEMS:
            rarity_counts[item.rarity] += 1

        # Calculate the chance of getting a common item
        rarities_with_items = [rarity for rarity, count in rarity_counts.items() if count > 0]
        common_rarity_chance = 1 - sum([self.get_loot_rarity_chance(rarity) for rarity in rarities_with_items if rarity != LootRarities.COMMON])
        self.common_chance = common_rarity_chance

        # Calculate the weight of each item in the pool
        rarity_item_weights = {
            rarity: self.get_loot_rarity_chance(rarity) / rarity_counts[rarity]
            for rarity in rarities_with_items
        }

        items = []
        weights = []
        for item in self.ITEMS:
            items.append(item)
            weights.append(rarity_item_weights[item.rarity])

        return items, weights

ITEM_POOL = [
    LootItem(Items.gamble_credit(1000), LootRarities.COMMON),
    LootItem(Items.gamble_credit(2000), LootRarities.COMMON),
    LootItem(Items.gamble_credit(3000), LootRarities.COMMON),

    LootItem(Items.shield(), LootRarities.UNCOMMON),
    LootItem(Items.gamble_credit(5000), LootRarities.UNCOMMON),
    LootItem(Items.bj_powerup('surrender'), LootRarities.UNCOMMON),

    LootItem(Items.mute_token(), LootRarities.RARE),
    LootItem(Items.deafen_token(), LootRarities.RARE),
    LootItem(Items.gamble_credit(7500), LootRarities.RARE),
    LootItem(Items.bj_powerup('show_dealer'), LootRarities.RARE),

    LootItem(Items.bubble(), LootRarities.EPIC),
    LootItem(Items.deflector(), LootRarities.EPIC),
    LootItem(Items.gamble_credit(10000), LootRarities.EPIC),
    # LootItem(Items.discount(25), LootRarities.EPIC),
    LootItem(Items.bj_powerup('show_next'), LootRarities.EPIC),

    LootItem(Items.bj_powerup('perfect_card'), LootRarities.LEGENDARY),
]


class CommonLootPool(LootPool):
    ITEMS = ITEM_POOL


Pools: dict[str, Type[LootPool]] = {
    'common': CommonLootPool
}
