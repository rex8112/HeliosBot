from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Dict, Optional

import discord

from ..exceptions import BidError, IdMismatchError

if TYPE_CHECKING:
    from .horse import Horse
    from ..stadium import Stadium
    from ..member import HeliosMember


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
    _default_settings = {
        'min_bid': 500,
        'max_bid': None,
        'snipe_protection': 300,
        'end_time': datetime.now().astimezone()
    }

    def __init__(self, auction: 'BasicAuction', horse_id: int):
        self.auction = auction
        self.horse_id = horse_id
        self.bids = []
        self.settings = self._default_settings.copy()

        self.new_bid = False

    @property
    def horse(self):
        return self.auction.stadium.horses.get(self.horse_id)

    @property
    def active(self):
        now = datetime.now().astimezone()
        snipe_time = timedelta(seconds=self.settings['snipe_protection'])
        return (now < self.settings['end_time']
                or now < self.get_highest_bidder_time() + snipe_time)

    @property
    def embed(self):
        horse = self.horse
        desc = ''
        if horse.get_flag('QUALIFIED'):
            desc += f'This horse is **Qualified**\n'
        win, loss = self.auction.stadium.get_win_loss(horse.records)
        today = datetime.now().astimezone().date()
        born = horse.date_born
        age = today - born
        desc += f'Raced in **{len(horse.records)}** eligible races.\n'
        desc += f'Record: **{win}/{loss}**\n'
        desc += f'Age: **{age.days}**\n'
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f'{horse.name} Listing',
            description=desc
        )
        bid = self.get_highest_bidder()
        embed.add_field(name='Auction Info',
                        value=(
                            f'Current Bid: `{bid.amount:,}` by '
                            f'<@{bid.bidder_id}>.\n'
                            f'Buyout: {self.settings.get("max_bid", None)}\n'
                            f'Time Left: '
                            f'<t:{int(self.end_time.timestamp())}:R>\n'
                        ))
        return embed

    @property
    def end_time(self):
        snipe_time = timedelta(seconds=self.settings['snipe_protection'])
        return max(self.settings['end_time'],
                   self.get_highest_bidder_time() + snipe_time)

    def get_highest_bidder(self) -> Bid:
        if len(self.bids) < 1:
            raise ValueError('Bids must not be empty')
        return self.bids[-1]

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
    _default_settings = {
        'start_time': datetime.now().astimezone(),
        'buy': False
    }

    def __init__(self, house: 'AuctionHouse'):
        self.house = house
        self.message: Optional[discord.Message] = None
        self.listings = []

        self.bid_update_list: List[List[discord.Message]] = []

    @property
    def stadium(self):
        return self.house.stadium

    def create_listings(self, horses: List['Horse']):
        for horse in horses:
            li = HorseListing(self, horse.id)
            self.add_listing(li)

    def add_listing(self, listing: HorseListing):
        self.listings.append(listing)
        self.bid_update_list.append(list())

    def to_json(self):
        if self.message:
            message = (self.message.channel.id, self.message.id)
        else:
            message = None
        return {
            'server': self.house.server.id,
            'listings': [li.to_json() for li in self.listings],
            'message': message
        }

    @classmethod
    def from_json(cls, house: 'AuctionHouse', data: Dict):
        if data['server'] != house.server.id:
            raise IdMismatchError('Id does not match current server')
        auction = cls(house)
        auction.listings = [HorseListing.from_json(auction, li)
                            for li in data['listings']]
        for _ in range(len(auction.listings)):
            auction.bid_update_list.append(list())
        if data['message']:
            channel_id, message_id = data['message']
            channel = house.server.guild.get_channel(channel_id)
            if channel:
                auction.message = channel.get_partial_message(message_id)


class RotatingAuction(BasicAuction):
    def __init__(self, house: 'AuctionHouse'):
        super().__init__(house)


class AuctionHouse:
    def __init__(self, stadium: 'Stadium'):
        self.stadium = stadium
        self.auctions = []

    @property
    def server(self):
        return self.stadium.server

    @property
    def bot(self):
        return self.server.bot

    async def setup(self):
        ...
