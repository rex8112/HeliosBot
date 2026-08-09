from discord.ext.commands import Bot

class HeliosBot(Bot):
    def __init__(self, command_prefix, *, intents, **kwargs):
        self.ready_once = True

        super().__init__(command_prefix, intents=intents, **kwargs)

    async def setup_hook(self):
        pass

    async def on_ready(self):
        pass