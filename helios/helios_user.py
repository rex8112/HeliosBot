import discord


class HeliosUser:
    def __init__(self, user: discord.User):
        self.user = user
        self.db = None

    @property
    def id(self):
        return self.user.id

    @classmethod
    async def new_user(cls, user: discord.User):
        user = cls(user)
