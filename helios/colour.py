import discord


class Colour:
    @staticmethod
    def helios():
        return discord.Colour.from_str('#FDB813')

    @staticmethod
    def success():
        return discord.Colour.green()

    @staticmethod
    def failure():
        return discord.Colour.red()

    @staticmethod
    def violation():
        return discord.Colour.red()
