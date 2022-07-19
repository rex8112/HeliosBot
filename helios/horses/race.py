import discord

from .horse import Horse


class RaceHorse:
    def __init__(self, horse: Horse, jockey=None):
        self.name = horse.name
        self.horse = horse
        self.jockey = jockey
        self.speed = 0
        self.progress = 0
        self.stamina = horse.stamina

    def accelerate(self):
        raise NotImplemented

    def tick(self) -> int:
        raise NotImplemented


class Race:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.horses: list[RaceHorse] = []
        self.length = 100
        self.phase = 0
