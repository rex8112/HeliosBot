import discord

from discord.ext import commands, tasks

from tools.database import db
from cogs.gacha import Deck, Card, Hero

class MarketOrder:

    __slots__ = [
        'bot', 'id', 'buy_order', 'value', 'card', 'guild',
        '_guild_id', 'creator', '_creator_id'
    ]
    def __init__(self, bot: commands.Bot, **kwargs):
        self.bot = bot

        self.guild = kwargs.get('guild')
        if self.guild:
            self._guild_id = self.guild.id
        else:
            self._guild_id = kwargs.get('guild_id')
        self.creator = kwargs.get('creator')
        if self.creator:
            self._creator_id = self.creator.id
        else:
            self._creator_id = kwargs.get('creator_id')

        self.id = kwargs.get('id')
        self.card = kwargs.get('card')
        self.buy_order = False
        self.value = 0
        if self.id:
            self._load()
        else:
            self._fill_discord_info()

    def set_buy_order(self, value):
        self.value = value
        self.buy_order = True

    def set_sell_order(self, value):
        self.value = value
        self.buy_order = False

    def _fill_discord_info(self):
        if self.guild is None:
            self.guild = self.bot.get_guild(self._guild_id)
        if self.creator is None and self.guild:
            self.creator = self.guild.get_member(self._creator_id)

    def _load(self, data=None):
        if data is None:
            data = db.get_market_order(id=self.id)[0]
        self._guild_id = data['guildID']
        self._creator_id = data['creatorID']
        buy_value = data['buyOrder']
        sell_value = data['sellOrder']
        if buy_value:
            self.value = buy_value
            self.buy_order = True
        else:
            self.value = sell_value
        self.card = Card.from_save_string(self.bot, data['cardSave'])
        self._fill_discord_info()

    def _save(self):
        db.set_market_order(
            self.id,
            guildID=self._guild_id,
            userID=self._creator_id,
            cardSave=self.card.get_save_string(),
            buyOrder=self.value if self.buy_order else None,
            sellOrder=self.value if not self.buy_order else None
        )

    def _new(self):
        self.id = db.add_market_order(self._guild_id, self._creator_id, self.card.get_save_string())

    @classmethod
    def new(cls, bot, creator: discord.Member, card: Card, buy_order: bool, value: int):
        instance = cls(bot, card=card, creator=creator, guild=creator.guild)
        instance._new()
        if buy_order:
            instance.set_buy_order(value)
        else:
            instance.set_sell_order(value)
        instance._save()
        return instance

    @classmethod
    def list_from_guild(cls, bot, guild_id: int):
        data = db.get_market_order(guildID=guild_id)
        orders = []
        for d in data:
            i = cls(bot)
            i._load(data=d)
            orders.append(i)
        return orders


class Market:
    def __init__(self, bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.orders = []

    def _update(self):
        self.orders = MarketOrder.list_from_guild(self.bot, self.guild.id)

    def get_overview(self):
        string = ''
        for i, order in enumerate(self.orders, start=1):
            string += f'{i:03}|{order.card.hero.name:<32}|{"Buy " if order.buy_order else "Sell"}|{order.value}\n'
        return string



class MarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(MarketCog(bot))