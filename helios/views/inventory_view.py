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
from typing import TYPE_CHECKING, Optional

from discord import ui, SelectOption, Interaction

if TYPE_CHECKING:
    from ..items import Item


__all__ = ('ItemSelectorView',)


class ItemSelectorView(ui.View):
    def __init__(self, items: list['Item']):
        super().__init__()
        self.items = items
        self.selected: Optional['Item'] = None
        self.last_interaction = None

        if items:
            self.item_select.options = [SelectOption(label=str(item), value=str(i)) for i, item in enumerate(items)]
        else:
            self.item_select.disabled = True
            self.item_select.placeholder = 'No items available'
            self.item_select.options = [SelectOption(label='No items available', value='0')]

    @ui.select(placeholder='Select an item')
    async def item_select(self, interaction: Interaction, select: ui.Select):
        self.selected = self.items[int(select.values[0])]
        await interaction.response.defer()
        self.stop()