from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..stadium import Stadium


class Bid:
    def __init__(self, bidder_id: int, listing_id: int, time: datetime):
        self.bidder_id = bidder_id
        self.listing_id = listing_id
        self.time = time


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
