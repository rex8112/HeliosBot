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
import random
from enum import Enum

from .image import get_card_images


class Suits(Enum):
    hearts = 'h'
    diamonds = 'd'
    clubs = 'c'
    spades = 's'


class Values(Enum):
    two = '2'
    three = '3'
    four = '4'
    five = '5'
    six = '6'
    seven = '7'
    eight = '8'
    nine = '9'
    ten = 'T'
    jack = 'J'
    queen = 'Q'
    king = 'K'
    ace = 'A'


class Card:
    def __init__(self, suit: Suits, value: Values):
        self.suit = suit
        self.value = value
        self.hidden = False

    def __str__(self):
        return f'{self.value.value}{self.suit.value}'

    def __repr__(self):
        return f'Card<{self.value.name} of {self.suit.name}>'

    def __eq__(self, o: object):
        if isinstance(o, Card):
            return self.suit == o.suit and self.value == o.value
        return NotImplemented

    def short(self):
        return f'{self.value.value}{self.suit.value[0]}'

    def bj_value(self):
        if self.value in [Values.jack, Values.queen, Values.king]:
            return 10
        if self.value == Values.ace:
            return 1
        if self.value == Values.ten:
            return 10
        return int(self.value.value)


class Deck:
    def __init__(self):
        self.cards: list[Card] = []
        self.reset()

    def __str__(self):
        return f'{len(self.cards)} cards'

    def __repr__(self):
        return f'Deck<{len(self.cards)} cards>'

    def __len__(self):
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)

    def __add__(self, o: object):
        if isinstance(o, Deck):
            cards = self.cards + o.cards
            deck = Deck()
            deck.cards = cards
            return deck
        return NotImplemented

    def __iadd__(self, o: object):
        if isinstance(o, Deck):
            self.cards += o.cards
            return self
        return NotImplemented

    @classmethod
    def from_cards(cls, cards: list[Card]):
        deck = cls()
        deck.cards = cards
        return deck

    @classmethod
    def new_many(cls, n: int):
        deck = None
        for _ in range(n):
            if deck is None:
                deck = cls()
            else:
                deck += cls()
        return deck

    def draw(self, hidden=False):
        card = self.cards.pop()
        card.hidden = hidden
        return card

    def draw_filter(self, filter_func, hidden=False):
        reversed_cards = list(reversed(self.cards))
        for card in reversed_cards:
            if filter_func(card):
                i = self.cards.index(card)
                card.hidden = hidden
                return self.cards.pop(i)
        return None

    def draw_to_hand(self, hand, hidden=False):
        hand.add_card(self.draw(hidden))

    def reset(self):
        self.cards = [Card(s, v) for s in Suits for v in Values]

    def shuffle(self):
        random.shuffle(self.cards)


class Hand:
    def __init__(self):
        self.cards: list[Card] = []

    def to_dict(self):
        return [str(card) for card in self.cards]

    @classmethod
    def from_dict(cls, data):
        hand = cls()
        hand.add_cards([Card(Suits(card[1]), Values(card[0])) for card in data])
        return hand

    def copy(self):
        return Hand.from_dict(self.to_dict())

    def add_card(self, card: Card):
        self.cards.append(card)

    def add_cards(self, cards: list[Card]):
        self.cards += cards

    def get_hand_bj_values(self, show_hidden=True, suppress_eleven=False) -> int:
        value = 0
        has_ace = False
        for card in self.cards:
            if card.hidden and not show_hidden:
                continue
            if card.bj_value() == 1:
                has_ace = True
            value += card.bj_value()

        if has_ace and value <= 11 and not suppress_eleven:
            value += 10
        return value

    def get_image(self):
        min_slots = 5
        return get_card_images(tuple(x.short() for x in self.cards if not x.hidden), max(min_slots, len(self.cards)))
