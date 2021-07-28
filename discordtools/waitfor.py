import asyncio
from typing import Callable
import discord

from discord.ext import commands

class WaitFor:
    def __init__(self, bot: commands.Bot, event: str, check: Callable = None, timeout: float = None) -> None:
        self.bot = bot
        self.event = event
        self.check = check
        self.timeout = timeout

        self.history = []
        self.last = None
        self.bot_messages = []
        self.messageable = None
        self.embed = None

    def set_embed(self, embed: discord.Embed):
        self.embed = embed

    def set_messageable(self, messageable: discord.abc.Messageable):
        self.messageable = messageable

    async def cleanup(self):
        if isinstance(self.messageable, commands.Context):
            self.messageable = self.messageable.channel
        if isinstance(self.messageable, discord.TextChannel):
            await self.messageable.delete_messages(self.bot_messages + self.history)
    
    async def run(self):
        if self.messageable and self.embed:
            message = await self.messageable.send(embed=self.embed)
            self.bot_messages.append(message)

        try:
            value = await self.bot.wait_for(self.event, check=self.check, timeout=self.timeout)
        except asyncio.TimeoutError:
            value =  None
        self.history.append(value)
        self.last = value
        return value