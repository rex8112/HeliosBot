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

