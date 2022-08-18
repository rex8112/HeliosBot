from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..stadium import Stadium


class Bid:
    def __init__(self, bidder_id: int, listing_id: int, amount: int,
                 time: datetime):
        self.bidder_id = bidder_id
        self.listing_id = listing_id
        self.amount = amount
        self.time = time

    @classmethod
    def from_data(cls, data: dict):
        return cls(
            bidder_id=data['bidder'],
            listing_id=data['listing'],
            amount=data['amount'],
            time=datetime.fromisoformat(data['time'])
        )

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Bid):
            return (o.bidder_id == self.bidder_id
                    and o.listing_id == self.listing_id
                    and o.amount == self.amount)
        else:
            return NotImplemented

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def serialize(self):
        return {
            'bidder': self.bidder_id,
            'listing': self.listing_id,
            'amount': self.amount,
            'time': self.time.isoformat()
        }


class HorseListing:
    def __init__(self, auction: 'Auction', horse_id: int):
        self.auction = auction
        self.horse_id = horse_id
        self.bids = []

    @property
    def horse(self):
        return self.auction.stadium.horses.get(self.horse_id)


class Auction:
    def __init__(self, house: 'AuctionHouse'):
        self.house = house
        self.listings = []

    @property
    def stadium(self):
        return self.house.stadium


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
