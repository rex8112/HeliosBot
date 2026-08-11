import discord

from .database import User


class HTTPClient:
    """A client to handle http requests to the Helios Server. Will temporarily just interact with the database directly."""
    def __init__(self):
        pass


    async def new_user(self, user: discord.User):
        user = User(id=user.id, username=user.name)
        await user.save()