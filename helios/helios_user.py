import discord


class HeliosUser:
    def __init__(self, user: discord.User):
        self.user = user

    @property
    def id(self):
        return self.user.id