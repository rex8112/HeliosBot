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

from discord import ui, Interaction


class AmountModal(ui.Modal, title='Amount'):
    amount = ui.TextInput(label='Amount', required=True)

    def __init__(self, *, default=None, timeout=30):
        super().__init__(timeout=timeout)
        if default:
            self.amount.default = default
        self.amount_selected = None

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            self.amount_selected = int(self.amount.value)
        except ValueError:
            await interaction.response.send_message(
                'You must provide an actual number.',
                ephemeral=True
            )
            return
        await interaction.response.defer()
        self.stop()


class PageModal(ui.Modal, title='Page'):
    page = ui.TextInput(label='Page', required=True)

    def __init__(self, *, default=None, timeout=30):
        super().__init__(timeout=timeout)
        if default:
            self.page.default = default
        self.page_selected = None

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            self.page_selected = int(self.page.value)
        except ValueError:
            await interaction.response.send_message(
                'You must provide an actual number.',
                ephemeral=True
            )
            return
        await interaction.response.defer()
        self.stop()


class SearchModal(ui.Modal, title='Search'):
    search = ui.TextInput(label='Search')

    def __init__(self, *, default=None, timeout=30):
        super().__init__(timeout=timeout)
        if default:
            self.search.default = default
        self.value = None

    async def on_submit(self, interaction: Interaction) -> None:
        self.value = self.search.value
        await interaction.response.defer()
        self.stop()

