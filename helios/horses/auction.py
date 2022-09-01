import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Dict, Optional

import discord

from .views import ListingView
from ..exceptions import BidError, IdMismatchError

if TYPE_CHECKING:
    from .horse import Horse
    from ..stadium import Stadium
    from ..member import HeliosMember
    from ..types.settings import (HorseListingSettings, AuctionSettings,
                                  GroupAuctionSettings,
                                  RotatingAuctionSettings)


class Bid:
    def __init__(self, bidder_id: int, amount: int,
                 time: datetime):
        self.bidder_id = bidder_id
        self.amount = amount
        self.time = time

    def __key(self):
        return self.bidder_id, self.amount

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Bid):
            return o.__key() == self.__key()
        else:
            return NotImplemented

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def __gt__(self, o: object) -> bool:
        if isinstance(o, Bid):
            return self.amount > o.amount
        else:
            return NotImplemented

    def __ge__(self, o: object) -> bool:
        if isinstance(o, Bid):
            return self.amount >= o.amount
        else:
            return NotImplemented

    def __lt__(self, o: object) -> bool:
        return not self.__ge__(o)

    def __le__(self, o: object) -> bool:
        return not self.__gt__(o)

    def to_json(self):
        return {
            'bidder': self.bidder_id,
            'amount': self.amount,
            'time': self.time.isoformat()
        }

    @classmethod
    def from_json(cls, data: dict):
        return cls(
            bidder_id=data['bidder'],
            amount=data['amount'],
            time=datetime.fromisoformat(data['time'])
        )


class HorseListing:
    _default_settings: HorseListingSettings = {
        'min_bid': 500,
        'max_bid': None,
        'snipe_protection': 300,
        'end_time': datetime.now().astimezone().isoformat()
    }

    def __init__(self, auction: 'BasicAuction', horse_id: int):
        self.auction = auction
        self.horse_id = horse_id
        self.bids: List[Bid] = []
        self.settings: HorseListingSettings = self._default_settings.copy()

        self.update_list: List[discord.Message] = []

        self.new_bid = False
        self.done = False
        self._task: Optional[asyncio.Task] = None

    @property
    def horse(self):
        return self.auction.stadium.horses.get(self.horse_id)

    @property
    def active(self):
        now = datetime.now().astimezone()
        if self.settings['max_bid']:
            bought = (self.get_highest_bidder().amount
                      >= self.settings['max_bid'])
        else:
            bought = False
        return now < self.end_time or bought

    @property
    def end_time(self):
        snipe_time = timedelta(seconds=self.settings['snipe_protection'])
        return max(datetime.fromisoformat(self.settings['end_time']),
                   self.get_highest_bidder_time() + snipe_time)

    @end_time.setter
    def end_time(self, value: datetime):
        self.settings['end_time'] = value.isoformat()

    def get_embed(self):
        horse = self.horse
        desc = ''
        if horse.get_flag('QUALIFIED'):
            desc += f'This horse is **Qualified**\n'
        win, loss = self.auction.stadium.get_win_loss(horse.records)
        today = datetime.now().astimezone().date()
        born = horse.date_born
        age = today - born
        desc += f'Raced in **{len(horse.records)}** eligible races.\n'
        desc += f'Record: **{win}W/{loss}L**\n'
        desc += f'Age: **{age.days}**\n'
        embed = discord.Embed(
            colour=(discord.Colour.orange()
                    if self.active else discord.Colour.red()),
            title=f'{horse.name} Listing',
            description=desc
        )
        if len(self.bids) > 0:
            bid = self.get_highest_bidder()
            cb = (f'Current Bid: {bid.amount:,} by '
                  f'<@{bid.bidder_id}>.\n')
        else:
            cb = ''
        embed.add_field(name='Auction Info',
                        value=(
                            f'{cb}'
                            f'Buyout: {self.settings.get("max_bid", None)}\n'
                            f'Time Left: '
                            f'<t:{int(self.end_time.timestamp())}:R>\n'
                        ))
        return embed

    def get_highest_bidder(self) -> Bid:
        if len(self.bids) < 1:
            raise ValueError('Bids must not be empty')
        return self.bids[-1]

    def get_highest_allowed_bid(self) -> Bid:
        if len(self.bids) < 1:
            raise ValueError('Bids must not be empty')
        server = self.auction.stadium.server
        for bid in reversed(self.bids):
            mem = server.members.get(bid.bidder_id)
            if mem:
                if bid.amount >= mem.points:
                    return bid
        return self.bids[0]

    def get_highest_bidder_time(self) -> datetime:
        if len(self.bids) > 0:
            high_bid = self.get_highest_bidder().time
        else:
            high_bid = datetime(2021, 1, 1).astimezone()
        return high_bid

    def get_price_history(self):
        return [b.amount for b in self.bids]

    def bid(self, member: 'HeliosMember', amount: int) -> Bid:
        b = Bid(member.member.id, amount, datetime.now().astimezone())
        if len(self.bids) > 0 and b <= self.bids[-1]:
            raise BidError('New bid must be higher')
        self.bids.append(b)
        self.new_bid = True
        return b

    def create_run_task(self, update_list: List[discord.Message]):
        if self._task is None or self._task.done():
            self._task = self.auction.stadium.server.bot.loop.create_task(
                self.run(update_list),
                name=f'HorseListing:{self.horse_id}'
            )

    async def run(self, update_list: List[discord.Message]):
        self.update_list = update_list
        while self.done is False:
            if self.new_bid or not self.active:
                tasks = []
                if not self.active:
                    if len(self.bids) > 0:
                        highest = self.get_highest_allowed_bid()
                        mem = self.auction.stadium.server.members.get(
                            highest.bidder_id
                        )
                        if mem.points >= highest.amount:
                            horse = self.horse
                            mem.points -= highest.amount
                            horse.owner = mem
                            horse.set_flag('QUALIFIED', True)
                            tasks.append(mem.save())
                            tasks.append(horse.save())
                            try:
                                await mem.member.send(
                                    f'You have purchased **{horse.name}** for'
                                    f' **{highest.amount:,}** points'
                                )
                            except discord.HTTPException:
                                ...
                    self.done = True
                self.new_bid = False
                remove = []
                for i, message in enumerate(self.update_list):
                    thirty_minutes = (datetime.now().astimezone()
                                      - timedelta(minutes=30))
                    expired = (isinstance(message.channel, discord.DMChannel)
                               and message.created_at < thirty_minutes)
                    if self.active and not expired:
                        tasks.append(message.edit(embed=self.get_embed(),
                                                  view=ListingView(self)))
                    else:
                        tasks.append(message.edit(embed=self.get_embed()))
                        remove.append(i)

                if len(tasks) > 0:
                    await asyncio.wait(tasks)

                for i in remove:
                    self.update_list.pop(i)
            await asyncio.sleep(1)

    def to_json(self):
        return {
            'horse': self.horse_id,
            'bids': [b.to_json() for b in self.bids],
            'settings': self.settings
        }

    @classmethod
    def from_json(cls, auction: 'BasicAuction', data: Dict):
        li = cls(auction, data['horse'])
        li.bids = [Bid.from_json(b) for b in data['bids']]
        li.settings = {**li._default_settings, **data['settings']}
        return li


class BasicAuction:
    _default_settings: AuctionSettings = {
        'start_time': datetime.now().astimezone().isoformat(),
        'buy': False
    }
    _type = 'basic'

    def __init__(self, house: 'AuctionHouse', channel: discord.TextChannel):
        self.house = house
        self.channel = channel
        self.message: Optional[discord.Message] = None
        self.listings: List[HorseListing] = []
        self.settings: AuctionSettings = self._default_settings.copy()

        self.bid_update_list: List[List[discord.Message]] = []

    @property
    def stadium(self):
        return self.house.stadium

    @property
    def type(self):
        return self._type

    @property
    def start_time(self) -> datetime:
        return datetime.fromisoformat(self.settings['start_time'])

    @property
    def pages(self) -> int:
        return math.ceil(len(self.listings) / 25)

    def is_done(self) -> bool:
        for listing in self.listings:
            if listing.active:
                return False
        return True

    def get_summary(self, page: int = 0):
        summary = (
            '```\n'
            'id  | Horse Name                 | Current   | Buyout    | '
            'Duration    \n')
        horses: List['Horse'] = [x.horse for x in self.listings]
        longest = max([len(x.name) for x in horses])
        longest = max(longest, len('horse name'))
        page_num = 25 * page
        for i, horse in enumerate(horses[page_num:25+page_num],
                                  start=1 + page_num):
            listing = self.listings[i-1]
            delta = datetime.now().astimezone() - listing.end_time
            hours = delta.total_seconds() // (60 * 60)
            hours = '<1' if hours < 1 else hours
            buyout = listing.settings.get('max_bid')
            bid = listing.get_highest_bidder()
            line = (f'{i:03} | {horse.name:{longest}} | {bid.amount:9,} | '
                    f'{buyout:9,} | in {hours:3} hours\n')
            summary += line
        summary += '```'
        return summary

    def create_listings(self, horses: List['Horse']):
        for horse in horses:
            li = HorseListing(self, horse.id)
            self.add_listing(li)

    def add_listing(self, listing: HorseListing):
        self.listings.append(listing)
        self.bid_update_list.append(list())

    async def run(self):
        ...

    def to_json(self):
        if self.message:
            message = (self.message.channel.id, self.message.id)
        else:
            message = None
        return {
            'type': self._type,
            'server': self.house.server.id,
            'listings': [li.to_json() for li in self.listings],
            'settings': self.settings,
            'channel': self.channel.id,
            'message': message
        }

    @classmethod
    def from_json(cls, house: 'AuctionHouse', data: Dict):
        if data['server'] != house.server.id:
            raise IdMismatchError('Id does not match current server')
        channel = house.server.guild.get_channel(data['channel'])
        auction = cls(house, channel)
        if data['type'] != auction._type:
            raise ValueError(f'{auction._type} if not of type {data["type"]}')
        auction.settings = {**auction._default_settings, **data['settings']}
        auction.listings = [HorseListing.from_json(auction, li)
                            for li in data['listings']]
        for _ in range(len(auction.listings)):
            auction.bid_update_list.append(list())
        if data['message']:
            channel_id, message_id = data['message']
            channel = house.server.guild.get_channel(channel_id)
            if channel:
                auction.message = channel.get_partial_message(message_id)


class GroupAuction(BasicAuction):
    _default_settings: GroupAuctionSettings = {
        **BasicAuction._default_settings,
        'duration': 60 * 60 * 24
    }
    _type = 'group'

    def __init__(self, house: 'AuctionHouse', channel: discord.TextChannel):
        super().__init__(house, channel)
        self.settings: GroupAuctionSettings = self._default_settings.copy()

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(seconds=self.settings['duration'])

    async def run(self):
        summary = self.get_summary()
        if datetime.now().astimezone() < self.start_time:
            return
        if self.message:
            if isinstance(self.message, discord.PartialMessage):
                self.message = await self.message.fetch()
            await self.message.edit(content=summary)
        else:
            self.message = await self.channel.send(content=summary)


class RotatingAuction(BasicAuction):
    _default_settings: RotatingAuctionSettings = {
        **BasicAuction._default_settings,
        'duration': 60 * 30,
        'announcement': 60 * 60 * 24
    }
    _type = 'rotating'

    def __init__(self, house: 'AuctionHouse', channel: discord.TextChannel):
        super().__init__(house, channel)
        self.settings: RotatingAuctionSettings = self._default_settings.copy()
        self.detail_messages: Dict[int, discord.Message] = {}

    @property
    def announcement_time(self) -> datetime:
        return self.start_time - timedelta(
            seconds=self.settings['announcement']
        )

    def create_listings(self, horses: List['Horse']):
        super().create_listings(horses)
        index = 1
        for listing in self.listings:
            duration = self.settings['duration']
            end = self.start_time + timedelta(seconds=duration * index)
            listing.end_time = end
            index += 1

    def get_schedule_embed(self):
        desc = ''
        for listing in self.listings:
            start_time = self.get_start_time(listing)
            desc += (f'<t:{int(start_time.timestamp())}:f> - '
                     f'**{listing.horse.name}** - ')
            if listing.active:
                desc += (f'Starting Price: **{listing.settings["min_bid"]:,}'
                         '**\n')
            else:
                desc += f'Finished\n'
        embed = discord.Embed(
            colour=discord.Colour.green(),
            title='Auction Schedule',
            description=desc
        )
        return embed

    def get_start_time(self, listing: HorseListing):
        return (datetime.fromisoformat(listing.settings['end_time'])
                - timedelta(seconds=self.settings['duration']))

    async def run(self):
        now = datetime.now().astimezone()
        if now >= self.announcement_time:
            if self.message is None:
                self.message = await self.channel.send(
                    embed=self.get_schedule_embed())
            elif isinstance(self.message, discord.PartialMessage):
                self.message = await self.message.fetch()
            else:
                await self.message.edit(embed=self.get_schedule_embed())
        if now < self.start_time:
            return  # Avoid looping before the auction is even ready.
        for i, listing in enumerate(self.listings):
            message = self.detail_messages.get(listing.horse_id)
            start = self.get_start_time(listing)
            end = listing.end_time
            if start <= now < end:
                if message is None:
                    message = await self.channel.send(
                        embed=listing.get_embed(), view=ListingView(listing))
                    self.detail_messages[listing.horse_id] = message
                    self.bid_update_list[i].append(message)
                    listing.create_run_task(self.bid_update_list[i])
                elif isinstance(message, discord.PartialMessage):
                    message = await message.fetch()
                    listing.new_bid = True
                    self.detail_messages[listing.horse_id] = message
                    self.bid_update_list[i].append(message)
                    listing.create_run_task(self.bid_update_list[i])


class AuctionHouse:
    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self.auctions: List[BasicAuction, RotatingAuction] = []

    @property
    def server(self):
        return self.stadium.server

    @property
    def bot(self):
        return self.server.bot

    async def run(self):
        cont = True
        rotating = list(filter(lambda x: x.type == 'rotating', self.auctions))
        group = list(filter(lambda x: x.type == 'group', self.auctions))
        if len(rotating) < 1:
            horses = random.sample(list(self.stadium.horses.values()), k=5)
            a = RotatingAuction(self, self.stadium.auction_channel)
            a.settings['start_time'] = (datetime.now().astimezone()
                                        + timedelta(minutes=1)).isoformat()
            a.create_listings(horses)
            self.auctions.append(a)
        if len(group) < 1:
            horses = random.sample(list(self.stadium.horses.values()), k=10)
            a = GroupAuction(self, self.stadium.auction_channel)
            a.settings['start_time'] = datetime.now().astimezone().isoformat()
            a.settings['duration'] = 60 * 60
            a.create_listings(horses)
            self.auctions.append(a)
        while cont:
            remove = []
            for i, auction in enumerate(self.auctions):
                await auction.run()
                if auction.is_done():
                    remove.append(i)
            for i in remove:
                self.auctions.pop(i)
            await asyncio.sleep(60)

    async def setup(self):
        ...
