import datetime
import math
import random
from typing import TYPE_CHECKING, Optional, List

import discord

from .breed import Breed
from .stats import StatContainer, Stat
from ..abc import HasSettings, HasFlags
from ..exceptions import IdMismatchError
from ..tools.settings import Item
from ..types.horses import HorseSerializable
from ..types.settings import HorseSettings

if TYPE_CHECKING:
    from ..member import HeliosMember
    from ..stadium import Stadium
    from .race import Record


class Horse(HasSettings, HasFlags):
    _default_settings: HorseSettings = {
        'gender': 'male',
        'age': 0,
        'likes': 0,
        'owner': None
    }
    _allowed_flags = [
        'QUALIFIED',
        'MAIDEN',
        'NEW',
        'PENDING',
        'DELETE',
        'REGISTERED'
    ]
    base_stat = 10

    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self._id = 0
        self.name = 'Unknown'
        self.breed = Breed('')
        self.date_born = datetime.datetime.now().astimezone().date()
        self.stats = StatContainer()
        self.stats['speed'] = Stat('speed', 0)
        self.stats['acceleration'] = Stat('acceleration', 0)
        self.settings: HorseSettings = self._default_settings.copy()
        self.records: list['Record'] = []
        self.flags = ['MAIDEN']

        self._new = True
        self._changed = False

    @property
    def id(self) -> int:
        return self._id

    @property
    def owner(self) -> Optional['HeliosMember']:
        if self.settings['owner']:
            return self.stadium.server.members.get(self.settings['owner'])
        return None

    @owner.setter
    def owner(self, value: 'HeliosMember'):
        if value is not None:
            self.settings['owner'] = value.id
        else:
            self.settings['owner'] = None

    @property
    def gender(self) -> str:
        return self.settings['gender']

    @property
    def age(self) -> int:
        today = datetime.datetime.now().astimezone().date()
        born = self.date_born
        age = today - born
        return age.days

    @property
    def is_new(self) -> bool:
        return self.id == 0

    @property
    def tier(self) -> int:
        return math.ceil(self.stats['speed'].value)

    @property
    def likes(self) -> int:
        return self.settings['likes']

    @likes.setter
    def likes(self, value: int) -> None:
        self.settings['likes'] = value

    @property
    def speed(self) -> float:
        return self.get_calculated_stat('speed')

    @property
    def acceleration(self) -> float:
        return self.get_calculated_stat('acceleration')

    @property
    def stamina(self) -> float:
        return self.breed.stat_multiplier['stamina'] * 500

    @property
    def registered(self) -> bool:
        return self.get_flag('REGISTERED')

    @property
    def value(self) -> int:
        value = 500
        if self.get_flag('QUALIFIED'):
            value += 250
        if not self.is_maiden():
            value += 250
        return value

    @property
    def quality(self) -> float:
        win, place, show, loss = self.stadium.get_win_place_show_loss(
            self.records)
        mmr = 1_000
        mmr += win * 30
        mmr += place * 10
        mmr += show * 5
        mmr += loss * -5
        if mmr < 5:
            mmr = 5
        return mmr

    @classmethod
    def new(cls, stadium: 'Stadium', name: str, breed: str, owner: Optional['HeliosMember'], *, num: int = None):
        horse = cls(stadium)
        horse.name = name
        horse.settings['owner'] = owner
        horse.generate_stats(num=num)
        return horse

    @classmethod
    def from_dict(cls, stadium: 'Stadium', data: dict):
        h = cls(stadium)
        h._deserialize(data)
        return h

    def get_inspect_embeds(self, *,
                           is_owner: bool = False) -> List[discord.Embed]:
        owner_id = (self.owner.member.id
                    if self.owner else self.stadium.owner.id)
        info = f'Owner: <@{owner_id}>\n'
        if is_owner:
            results = self.stadium.get_win_place_show_loss(self.records)
            info += (f'Record: {results[0]}W/{results[1]}P/'
                     f'{results[2]}S/{results[3]}L\n')
        else:
            win, loss = self.stadium.get_win_loss(self.records)
            info += f'Record: {win}W/{loss}L\n'
        info += (f'Breed: {self.breed.name}\n'
                 f'Gender: {self.gender}\n'
                 f'Age: {self.age}')
        embeds = []
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title=self.name,
            description=info
        )
        embeds.append(embed)
        if self.get_flag('DELETE'):
            embed2 = discord.Embed(
                colour=discord.Colour.red(),
                title='PENDING DELETION',
                description=('This horse is being prepared to be '
                             '"let go." If you believe this is in error '
                             'please contact rex8112#1200 immediately as '
                             'the horse has limited time remaining.')
            )
            embeds.append(embed2)
        return embeds

    def get_graded_points_since(self, date: datetime.date) -> int:
        points = 0
        for rec in self.records:
            if rec.date < date:
                continue
            points += rec.points
        return points

    def pay(self, amount: float):
        owner = self.owner
        if owner:
            owner.points += amount

    def is_maiden(self):
        return self.get_flag('MAIDEN')

    def make_qualified(self):
        self.set_flag('QUALIFIED', True)
        self.clear_basic_records()

    def clear_basic_records(self):
        self.records = list(filter(lambda x: x.race_type != 'basic',
                                   self.records))

    def get_calculated_stat(self, stat: str):
        return (Horse.base_stat + self.stats[stat].value) * self.breed.stat_multiplier[stat]

    def generate_stats(self, num=None):
        if not num:
            num = random.choices(
                range(1, 11),
                weights=(33, 20, 15, 10, 7, 5, 4, 3, 2, 1),
                k=1
            )[0]
        speed_diff = round(random.uniform(0, 0.5), 2)
        accel_diff = round(random.uniform(0, 0.5), 2)
        rand_speed = num - speed_diff
        rand_accel = num - accel_diff
        self.stats['speed'].value = rand_speed
        self.stats['acceleration'].value = rand_accel

    def serialize(self) -> HorseSerializable:
        data: HorseSerializable = {
            'server': self.stadium.server.id,
            'id': self._id,
            'name': self.name,
            'breed': self.breed.name,
            'stats': self.stats.serialize(),
            'born': Item.serialize(self.date_born),
            'settings': Item.serialize_dict(self.settings),
            'flags': self.flags
        }
        if self._new:
            data['id'] = None
        return data

    def _deserialize(self, data: HorseSerializable):
        if data['server'] != self.stadium.server.id:
            raise IdMismatchError('This horse does not belong to this stadium.')
        self._id = data['id']
        self.name = data['name']
        self.breed = Breed(data['breed'])
        self.stats = StatContainer.from_dict(data['stats'])
        self.date_born = Item.deserialize(data['born'])
        settings = Item.deserialize_dict(data['settings'],
                                         guild=self.stadium.guild,
                                         bot=self.stadium.server.bot)
        self.settings = {**self._default_settings, **settings}
        self.flags = data['flags']
        self._new = False

    async def save(self):
        if self.is_new:
            data = self.serialize()
            del data['id']
            new_data = await self.stadium.server.bot.helios_http.post_horse(data)
            self._id = new_data['id']
            self._new = False
        else:
            await self.stadium.server.bot.helios_http.patch_horse(self.serialize())

    async def delete(self):
        await self.stadium.server.bot.helios_http.del_horse(self._id)
        del self.stadium.horses[self._id]
