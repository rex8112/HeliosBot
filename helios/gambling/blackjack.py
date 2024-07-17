#  MIT License
#
#  Copyright (c) 2024 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
from typing import TYPE_CHECKING

from ..member import HeliosMember
from .cards import Hand, Deck, Card
from .image import get_member_icon

if TYPE_CHECKING:
    from PIL import Image


class BlackJack:
    def __init__(self):
        self.players: list[HeliosMember] = []
        self.icons: list['Image'] = []
        self.deck: Deck = Deck.new_many(2)
        self.hands: list[list[Hand]] = [[Hand()]]
        self.bets: list[list[int]] = []

        self.dealer_icon: 'Image' = None

    def reset(self):
        self.players = []
        self.icons = []
        self.deck = Deck.new_many(2)
        self.hands = [Hand()]
        self.bets = []

    async def add_player(self, player: HeliosMember):
        self.players.append(player)
        self.hands.append([Hand()])
        self.bets.append([0])
        self.icons.append(await get_member_icon(player))

    async def remove_player(self, player: HeliosMember):
        index = self.players.index(player)
        self.players.pop(index)
        self.hands.pop(index)
        self.bets.pop(index)
        self.icons.pop(index)

    def get_hands(self, player: HeliosMember):
        index = self.players.index(player)
        return self.hands[index]

    def get_bets(self, player: HeliosMember):
        index = self.players.index(player)
        return self.bets[index]

