import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Dict, Optional

import discord

from .views import ListingView, GroupAuctionView
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
    _default_settings: 'HorseListingSettings' = {
        'min_bid': 500,
        'max_bid': None,
        'snipe_protection': 300,
        'end_time': datetime.now().astimezone().isoformat()
    }

    def __init__(self, auction: 'BasicAuction', horse_id: int):
        self.auction = auction
        self.horse_id = horse_id
        self.bids: List[Bid] = []
        self.settings: 'HorseListingSettings' = self._default_settings.copy()

        self.update_list: List[discord.Message] = []

        self.new_bid = False
        self.cancelled = False
        self.done = False
        self._task: Optional[asyncio.Task] = None

    @property
    def horse(self):
        return self.auction.stadium.horses.get(self.horse_id)

    @property
    def active(self):
        now = datetime.now().astimezone()
        if self.settings['max_bid']:
            try:
                bought = (self.get_highest_bidder().amount
                          >= self.settings['max_bid'])
            except ValueError:
                bought = False
        else:
            bought = False
        return now < self.end_time and not bought and not self.cancelled

    @property
    def end_time(self):
        snipe_time = timedelta(seconds=self.settings['snipe_protection'])
        return max(datetime.fromisoformat(self.settings['end_time']),
                   self.get_highest_bidder_time() + snipe_time)

    @end_time.setter
    def end_time(self, value: datetime):
        self.settings['end_time'] = value.isoformat()

    @staticmethod
    def can_bid(member: 'HeliosMember', amount: int) -> bool:
        return (len(member.horses) < member.max_horses
                and member.points >= amount)

    def get_embed(self):
        horse = self.horse
        desc = ''
        if horse.get_flag('QUALIFIED'):
            desc += f'This horse is **Qualified**\n'
        win, loss = self.auction.stadium.get_win_loss(horse.records)
        desc += f'Raced in **{len(horse.records)}** eligible races.\n'
        desc += f'Record: **{win}W/{loss}L**\n'
        desc += f'Age: **{horse.age}**\n'
        embed = discord.Embed(
            colour=(discord.Colour.orange()
                    if self.active else discord.Colour.red()),
            title=f'{horse.name} Listing',
            description=desc,
            timestamp=datetime.now().astimezone()
        )
        if len(self.bids) > 0:
            bid = self.get_highest_bidder()
            cb = (f'Current Bid: {bid.amount:,} by '
                  f'<@{bid.bidder_id}>.\n')
        else:
            cb = ''
        time_string = f'<t:{int(self.end_time.timestamp())}:R>\n'
        if not self.active:
            winner = self.get_highest_allowed_bid()
            cb = f'Winning Bid: {winner.amount:,} by <@{winner.bidder_id}>.\n'
            time_string = '**Finished**\n'
        embed.add_field(name='Auction Info',
                        value=(
                            f'{cb}'
                            f'Buyout: {self.settings.get("max_bid", None)}\n'
                            f'Time Left: '
                            f'{time_string}'
                        ))
        return embed

    def get_highest_bidder(self) -> Bid:
        if len(self.bids) < 1:
            raise ValueError('Bids must not be empty')
        return self.bids[-1]

    def get_highest_allowed_bid(self) -> Optional[Bid]:
        server = self.auction.stadium.server
        for bid in reversed(self.bids):
            mem = server.members.get(bid.bidder_id)
            if mem:
                if self.can_bid(mem, bid.amount):
                    return bid
        return None

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

    def cancel(self):
        self.cancelled = True
        self.done = True
        self.auction.settings['any_canceled'] = True
        self.bids.clear()

    async def run(self, update_list: List[discord.Message]):
        self.update_list = update_list
        while self.done is False:
            try:
                if self.new_bid or not self.active:
                    tasks = []
                    if not self.active:
                        self.horse.likes = 0
                        if len(self.bids) > 0:
                            highest = self.get_highest_allowed_bid()
                            if highest is not None:
                                mem = self.auction.stadium.server.members.get(
                                    highest.bidder_id
                                )
                                if mem.points >= highest.amount:
                                    horse = self.horse
                                    mem.points -= highest.amount
                                    horse.owner = mem
                                    horse.make_qualified()
                                    horse.set_flag('PENDING', False)
                                    await mem.save()
                                    try:
                                        await mem.member.send(
                                            f'You have purchased **{horse.name}** '
                                            f'for **{highest.amount:,}** points'
                                        )
                                    except (discord.HTTPException,
                                            discord.Forbidden):
                                        ...
                        self.horse.set_flag('NEW', False)
                        await self.horse.save()
                        self.done = True
                    self.new_bid = False
                    remove = []
                    self.auction.changed = True
                    for i, message in enumerate(self.update_list):
                        if self.active:
                            tasks.append(message.edit(embed=self.get_embed(),
                                                      view=ListingView(self)))
                        else:
                            tasks.append(message.edit(embed=self.get_embed(),
                                                      view=None))
                            remove.append(message)

                    if len(tasks) > 0:
                        await asyncio.wait(tasks)

                    for i in remove:
                        self.update_list.remove(i)
                await asyncio.sleep(1)
            except Exception as e:
                print(type(e).__name__, e)

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
        now = datetime.now().astimezone()
        if now > li.end_time - timedelta(minutes=10):
            li.cancel()
        return li


class BasicAuction:
    _default_settings: 'AuctionSettings' = {
        'start_time': datetime.now().astimezone().isoformat(),
        'buy': False,
        'any_canceled': False
    }
    _type = 'basic'

    def __init__(self, house: 'AuctionHouse', channel: discord.TextChannel):
        self._id = 0
        self._listings_done = 0
        self.house: 'AuctionHouse' = house
        self.channel: discord.TextChannel = channel
        self.name: str = 'Auction'
        self.message: Optional[discord.Message] = None
        self.listings: List[HorseListing] = []
        self.settings: 'AuctionSettings' = self._default_settings.copy()

        self.bid_update_list: List[List[discord.Message]] = []
        self.changed = False

    @property
    def id(self) -> int:
        return self._id

    @property
    def stadium(self):
        return self.house.stadium

    @property
    def type(self):
        return self._type

    @property
    def start_time(self) -> datetime:
        return datetime.fromisoformat(self.settings['start_time'])

    @start_time.setter
    def start_time(self, value: datetime):
        self.settings['start_time'] = value.isoformat()

    @property
    def pages(self) -> int:
        return math.ceil(len(self.listings) / 25)

    def is_new(self):
        return self._id == 0

    def get_horse_ids(self) -> List[int]:
        ids = []
        for listing in self.listings:
            ids.append(listing.horse_id)
        return ids

    def get_horses(self) -> Dict[int, 'Horse']:
        horses = {}
        for listing in self.listings:
            horse = listing.horse
            horses[horse.id] = horse
        return horses

    def is_active(self) -> bool:
        now = datetime.now().astimezone()
        if now >= self.start_time and not self.is_done():
            return True
        return False

    def is_done(self) -> bool:
        for listing in self.listings:
            if listing.active:
                return False
        return True

    def amount_done(self) -> int:
        done = 0
        for listing in self.listings:
            if not listing.active:
                done += 1
        return done

    def should_save(self) -> bool:
        new_done = self.amount_done()
        if new_done != self._listings_done or self.changed:
            self.changed = False
            self._listings_done = new_done
            return True
        return False

    def get_summary(self, page: int = 0):
        summary = (
            '```\n'
            'id  | Horse Name    | W/L   | Current   | Starting  | '
            'Buyout    | Duration    \n')
        horses: List['Horse'] = [x.horse for x in self.listings]
        page_num = 25 * page
        for i, horse in enumerate(horses[page_num:25+page_num],
                                  start=1 + page_num):
            listing = self.listings[i-1]
            delta = listing.end_time - datetime.now().astimezone()
            hours = int(delta.total_seconds() // (60 * 60))
            hours = ' <1' if hours < 1 else hours
            buyout = listing.settings.get('max_bid')
            if len(horse.name) > 13:
                name = f'{horse.name[:10]}...'
            else:
                name = horse.name
            win, loss = self.stadium.get_win_loss(horse.records)
            try:
                ratio = win / len(horse.records)
            except ZeroDivisionError:
                ratio = 0
            if len(listing.bids) > 0:
                bid = listing.get_highest_bidder().amount
            else:
                bid = 0
            start = listing.settings['min_bid']
            if buyout is None:
                buyout = 0
            duration = f'in {hours:3} hours'
            if listing.cancelled:
                duration = 'cancelled   '
            elif listing.done:
                duration = 'finished    '
            line = (f'{i:03} | {name:13} | {ratio:5.0%} | {bid:9,} | '
                    f'{start:9,} | {buyout:9,} | {duration}\n')
            summary += line
        summary += '```'
        return summary

    def create_listings(self, horses: List['Horse']):
        for horse in horses:
            li = HorseListing(self, horse.id)
            li.settings['min_bid'] = horse.value
            if self.settings['buy']:
                li.settings['max_bid'] = li.settings['min_bid']
            self.add_listing(li)

    def add_listing(self, listing: HorseListing):
        self.listings.append(listing)
        self.bid_update_list.append(list())

    async def run(self):
        if self.settings['any_canceled'] and self.is_done():
            self.settings['any_canceled'] = False
            # self.house.redo_canceled_listings(self)
        if self.should_save() or self.is_new():
            await self.save()

    async def delete(self):
        return await self.stadium.server.bot.helios_http.del_auction(self._id)

    def to_json(self):
        if self.message:
            message = (self.message.channel.id, self.message.id)
        else:
            message = tuple()
        return {
            'id': self._id,
            'name': self.name,
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
        auction._id = data['id']
        auction.name = data['name']
        if data['type'] != auction._type:
            raise ValueError(f'{auction._type} is not of type {data["type"]}')
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
        auction.should_save()
        return auction

    @classmethod
    async def from_id(cls, house: 'AuctionHouse', id: int):
        data = await house.stadium.server.bot.helios_http.get_auction(
            auction_id=id
        )
        return cls.from_json(house, data)

    async def save(self):
        data = self.to_json()
        if self.is_new():
            del data['id']
            d = await self.stadium.server.bot.helios_http.post_auction(data)
            self._id = d['id']
        else:
            await self.stadium.server.bot.helios_http.patch_auction(data)


class GroupAuction(BasicAuction):
    _default_settings: 'GroupAuctionSettings' = {
        **BasicAuction._default_settings,
        'duration': 60 * 60 * 24
    }
    _type = 'group'

    def __init__(self, house: 'AuctionHouse', channel: discord.TextChannel):
        super().__init__(house, channel)
        self.settings: 'GroupAuctionSettings' = self._default_settings.copy()

    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(seconds=self.settings['duration'])

    def create_listings(self, horses: List['Horse']):
        super().create_listings(horses)
        for listing in self.listings:
            end = (self.start_time
                   + timedelta(seconds=self.settings['duration']))
            listing.end_time = end

    async def run(self):
        summary = self.get_summary()
        summary = f'**{self.name}**\n{summary}'
        await super().run()
        if datetime.now().astimezone() < self.start_time:
            return
        view = GroupAuctionView(self)
        new = False
        if self.message:
            if type(self.message) == discord.PartialMessage:
                self.message = await self.message.fetch()
                new = True
            if self.is_done():
                await self.message.edit(content=summary, view=None)
            else:
                await self.message.edit(content=summary, view=view)
        else:
            self.message = await self.channel.send(content=summary, view=view)
            await self.save()
            new = True
        if new:
            for i, listing in enumerate(self.listings):
                if listing.active or listing.horse.owner is None:
                    listing.create_run_task(self.bid_update_list[i])
                else:
                    listing.done = True


class RotatingAuction(BasicAuction):
    _default_settings: 'RotatingAuctionSettings' = {
        **BasicAuction._default_settings,
        'duration': 60 * 30,
        'announcement': 60 * 60 * 24
    }
    _type = 'rotating'

    def __init__(self, house: 'AuctionHouse', channel: discord.TextChannel):
        super().__init__(house, channel)
        self.settings: 'RotatingAuctionSettings' = \
            self._default_settings.copy()
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
            title=f'{self.name} Schedule',
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
            elif type(self.message) == discord.PartialMessage:
                self.message = await self.message.fetch()
            else:
                await self.message.edit(embed=self.get_schedule_embed())
        await super().run()
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
                elif type(message) == discord.PartialMessage:
                    message = await message.fetch()
                    listing.new_bid = True
                    self.detail_messages[listing.horse_id] = message
                    self.bid_update_list[i].append(message)
                    listing.create_run_task(self.bid_update_list[i])


class AuctionHouse:
    NEW_AUCTION = 6
    TOP_AUCTION = 5
    DIE_AUCTION = 4

    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self.once = True
        self.auctions: List[BasicAuction, RotatingAuction] = []

    @property
    def server(self):
        return self.stadium.server

    @property
    def bot(self):
        return self.server.bot

    def get_horse_ids(self) -> List[int]:
        ids = []
        for auction in self.auctions:
            ids.extend(auction.get_horse_ids())
        return ids

    def get_horses(self) -> Dict[int, 'Horse']:
        horses = {}
        for auction in self.auctions:
            horses.update(auction.get_horses())
        return horses

    def redo_canceled_listings(self, auction: 'BasicAuction'):
        canceled_horses = []
        for listing in auction.listings:
            if listing.cancelled:
                canceled_horses.append(listing.horse)
        a = GroupAuction(self, self.stadium.auction_channel)
        now = datetime.now().astimezone().replace(hour=11, minute=0,
                                                  second=0, microsecond=0)
        a.start_time = now + timedelta(days=1)
        a.settings['duration'] = 60 * 60 * 6
        a.name = 'Redo Auction'
        self.auctions.append(a)

    def create_top_auction(self, horses: List['Horse'], *, keep: int):
        now = datetime.now().astimezone()
        amount_of_listings = 24
        horses = horses.copy()
        amount_of_listings = min(amount_of_listings, len(horses) - keep)
        if amount_of_listings < 1:
            return
        random.shuffle(horses)
        horses = sorted(horses, key=lambda x: x.likes, reverse=True)
        a = RotatingAuction(self, self.stadium.special_auction_channel)
        a.name = 'Weekly Top Auction'
        a.start_time = (now.replace(hour=12, minute=0,
                                    second=0, microsecond=0)
                        + timedelta(days=1))
        a.create_listings(horses[:amount_of_listings])
        self.auctions.append(a)

    def create_new_auctions(self, horses: List['Horse']):
        now = datetime.now().astimezone()
        new_horses = horses
        auctions = math.ceil(len(new_horses) / 20)
        new_auctions = list(filter(lambda x: x.name == 'New Horse Auction',
                                   self.auctions))
        if len(new_auctions) > 0:
            auctions = 0
        for i in range(auctions):
            end = (i + 1) * 20
            horses = new_horses[i*20:end]
            a = GroupAuction(self, self.stadium.auction_channel)
            a.name = 'New Horse Auction'
            a.start_time = now.replace(hour=12, minute=0,
                                       second=0, microsecond=0)
            a.settings['duration'] = 60 * 60 * 24
            a.settings['buy'] = True
            a.create_listings(horses)
            self.auctions.append(a)

    def create_final_auctions(self,
                              horses: List['Horse']) -> List['GroupAuction']:
        now = datetime.now().astimezone()
        final_auctions = list(
            filter(lambda x: x.name == 'Last Chance Auction',
                   self.auctions)
        )
        auction_list = []
        if len(final_auctions) > 0:
            auctions = 0
        else:
            auctions = math.ceil(len(horses) / 20)
        for i in range(auctions):
            end = (i + 1) * 20
            tmp_horses = horses[i*20:end]
            a = GroupAuction(self, self.stadium.auction_channel)
            a.name = 'Last Chance Auction'
            a.start_time = now.replace(hour=12, minute=0,
                                       second=0, microsecond=0)
            a.settings['duration'] = 60 * 60 * 24
            a.create_listings(tmp_horses)
            self.auctions.append(a)
            auction_list.append(a)
        return auction_list

    async def run(self):
        remove = []
        for i, auction in enumerate(self.auctions):
            await auction.run()
            if auction.is_done():
                await auction.delete()
                remove.append(auction)
        for i in remove:
            try:
                self.auctions.remove(i)
            except ValueError:
                ...

    async def setup(self, auctions_data: Optional[List] = None):
        if auctions_data is None:
            auctions_data = await self.server.bot.helios_http.get_auction(
                server=self.server.id
            )
            if auctions_data is None:
                auctions_data = []
        for data in auctions_data:
            if data['type'] == 'rotating':
                a = RotatingAuction.from_json(self, data)
            elif data['type'] == 'group':
                a = GroupAuction.from_json(self, data)
            else:
                continue
            self.auctions.append(a)
