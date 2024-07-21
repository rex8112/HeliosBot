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
import io
import math

import requests
from typing import Union, TYPE_CHECKING, Optional, Literal

import numpy as np
from PIL import Image, ImageDraw, ImageOps, ImageFont
from pokerkit import Card as PCards

if TYPE_CHECKING:
    from ..member import HeliosMember
    from .cards import Card, Hand
    from aiohttp import ClientSession


def get_card_images(cards: tuple[Union[str, PCards], ...], slots: int) -> io.BytesIO:
    if len(cards) > slots:
        raise ValueError('Cards must be less than the slots.')

    if len(cards) >= 1 and isinstance(cards[0], PCards):
        cards = [f'{x.rank}{x.suit}' for x in cards]

    width = 10 + (155 * slots)
    background = Image.new(mode='RGBA', size=(width, 220), color=(255, 0, 0, 0))
    x = 10
    for card in cards:
        try:
            card = Image.open(f'./helios/resources/cards/{card}.png')
            background.paste(card, (x, 10), mask=card)
        except FileNotFoundError:
            ...
        x += 155
    b = io.BytesIO()
    background.save(b, 'PNG')
    b.seek(0)
    return b


class BlackjackHandImage:
    def __init__(self, hand: 'Hand', icon: 'Image', name: str, bet: int):
        self.hand = hand
        self.icon: Image = icon.copy().resize((64, 64)).convert('RGBA')
        self.name = name
        self.bet = bet

        self.padding = 20
        self.card_spots = 5
        self.card_width = 145
        self.card_gap = -105
        self.card_height = 200

        self._background: Optional[Image] = None
        self._currently_shown_cards: list['Card'] = []
        self._current_image: Optional[Image] = None

    def get_width(self) -> int:
        return (self.padding + (self.card_width * self.card_spots) + (self.card_gap * (self.card_spots - 1))
                + self.padding)

    def get_height(self) -> int:
        return self.padding + self.icon.height + 10 + self.card_height + self.padding

    def get_background(self, redraw=False) -> Image:
        if not self._background or redraw:
            background = Image.new(mode='RGBA', size=(self.get_width(), self.get_height()), color=(255, 0, 0, 0))
            draw = ImageDraw.Draw(background)
            draw.rounded_rectangle(((0, 0), background.size), 32, fill='black')
            background.paste(self.icon, (self.padding, self.padding), mask=self.icon)

            start_x = self.padding + self.icon.width + 10
            draw.text((start_x, self.padding), self.name, fill='white', font_size=32)
            if self.bet:
                draw.text((start_x, self.padding + 30), f'Bet: {self.bet:,}', fill='white', font_size=24)

            self._background = background
            del draw
        return self._background

    def get_diff(self):
        new_cards = self.hand.cards
        diff = []
        for i, card in enumerate(new_cards):
            if i >= len(self._currently_shown_cards):
                diff.append(card)
            elif card != self._currently_shown_cards[i]:
                return None
        return diff

    def draw_outline(self, result: Literal['win', 'push', 'lose', 'turn'] = 'turn') -> Image:
        if self._current_image is None:
            raise ValueError('No current image to draw cards on.')
        if result == 'turn':
            color = 'green'
        elif result == 'win':
            color = 'green'
        elif result == 'push':
            color = 'yellow'
        else:
            color = 'red'
        img = self._current_image.copy()
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(((0, 0), img.size), 32, outline=color, width=5)
        del draw
        return img

    def draw_cards(self, cards: list['Card']):
        if self._current_image is None:
            raise ValueError('No current image to draw cards on.')
        if len(self._currently_shown_cards) >= self.card_spots:
            card_x = self.padding + ((len(self._currently_shown_cards) - self.card_spots)
                                     * (self.card_width + self.card_gap))
        else:
            card_x = self.padding + (len(self._currently_shown_cards) * (self.card_width + self.card_gap))
        card_y = self._current_image.height - self.card_height - self.padding
        card_num = len(self._currently_shown_cards)
        for card in cards:
            if card_num == self.card_spots:
                card_x = self.padding
            if card_num >= self.card_spots:
                y = card_y + self.card_height // 3
            else:
                y = card_y
            x = card_x
            if card.hidden:
                # card = Image.open('./helios/resources/cards/back.png')
                # background.paste(card, (x, y), mask=card)
                continue
            else:
                try:
                    img = Image.open(f'./helios/resources/cards/{card.short()}.png')
                    self._current_image.paste(img, (x, y), mask=img)
                except FileNotFoundError:
                    ...
            card_x += self.card_width + self.card_gap
            card_num += 1
        if len(cards):
            self.draw_hand_value()

    def draw_hand_value(self):
        font = ImageFont.load_default(62)
        draw = ImageDraw.Draw(self._current_image)
        bbox = font.getbbox('32')

        draw.rectangle(((self._current_image.width - self.padding - bbox[2], self.padding),
                        (self._current_image.width - self.padding, self.padding + bbox[3])),
                       fill='black')
        hand_value = self.hand.get_hand_bj_values(False)
        draw.text((self._current_image.width - self.padding, self.padding), str(hand_value), fill='white',
                  font_size=62, anchor='rt')
        del draw

    def get_image(self, result: Literal['win', 'push', 'lose', 'turn'] = '', *, redraw=False) -> Image:
        diff = self.get_diff()

        if self._current_image is None or diff is None or redraw:
            self._current_image = self.get_background(redraw).copy()
            self._currently_shown_cards = []
            self.draw_cards(self.hand.cards)
        else:
            self.draw_cards(diff)
        self._currently_shown_cards = self.hand.cards.copy()

        if result:
            return self.draw_outline(result)

        return self._current_image


class BlackjackImage:
    def __init__(self, dealer_hand: 'BlackjackHandImage', hands: list['BlackjackHandImage'], current_hand: int = 0,
                 id: int = 0, winnings: list = None):
        if winnings is None:
            winnings = []
        self.dealer_hand = dealer_hand
        self.hands = hands
        self.current_hand = current_hand
        self.winnings = winnings
        self.id = id

        self.padding = 20
        self.wrap = 4

        self._background: Optional[Image] = None
        self._current_image: Optional[Image] = None

    def get_width(self) -> int:
        return self.padding + sum(self.dealer_hand.get_width() + self.padding for _ in range(self.wrap))

    def get_hands_height(self) -> int:
        hand_height = self.dealer_hand.get_height() if len(self.hands) < self.wrap + 1 \
            else self.dealer_hand.get_height() * 2 + self.padding
        return hand_height

    def get_height(self) -> int:
        hand_height = self.get_hands_height()

        value = (self.padding
                 + self.dealer_hand.get_height()
                 + self.padding
                 + 150
                 + self.padding
                 + hand_height
                 + self.padding)
        return value

    def get_background(self) -> Image:
        if not self._background:
            background = Image.new(mode='RGBA', size=(self.get_width(), self.get_height()), color=(255, 0, 0, 0))
            draw = ImageDraw.Draw(background)
            draw.text((self.padding, self.padding), f'#{self.id}', fill='white', font_size=64)
            del draw
            self._background = background
        return self._background

    def draw_dealer_hand(self):
        hand = self.dealer_hand.get_image()
        h_width, h_height = hand.size
        b_width = self._current_image.width

        hand_mid = h_width // 2
        background_mid = b_width // 2

        self._current_image.paste(hand, (background_mid - hand_mid, self.padding), mask=hand)

    def draw_hands(self):
        if len(self.hands) == 0:
            return
        h_width = self.hands[0].get_width()
        h_height = self.hands[0].get_height()
        b_height = self._current_image.height
        y = b_height - self.get_hands_height() - self.padding
        x = self.padding
        for i, hand in enumerate(self.hands):
            if i == self.wrap:
                y += h_height + self.padding
                x = self.padding
            if i == self.current_hand:
                hand_image = hand.get_image('turn')
            elif len(self.winnings) > 0:
                winnings = self.winnings[i]
                if winnings == 0:
                    hand_image = hand.get_image('lose')
                elif winnings == hand.bet:
                    hand_image = hand.get_image('push')
                else:
                    hand_image = hand.get_image('win')
            else:
                hand_image = hand.get_image()
            self._current_image.paste(hand_image, (x, y), mask=hand_image)
            x += h_width + self.padding

    def draw_status(self, status: str):
        draw = ImageDraw.Draw(self._current_image)
        f_size = 70
        font = ImageFont.load_default(f_size)
        bbox = font.getbbox(status)

        b_height = self._current_image.height
        bh_middle_start = self.padding + self.dealer_hand.get_height()
        bh_middle_end = b_height - self.get_hands_height() - self.padding
        center_h = bh_middle_end - bh_middle_start
        bh_middle = center_h // 2 + bh_middle_start

        bw_middle = self._current_image.width // 2
        boxh_middle = f_size // 2
        boxw_middle = bbox[2] // 2
        draw.text((bw_middle - boxw_middle, bh_middle - boxh_middle), status, fill='white', font_size=70)
        del draw

    def get_image(self, status: str = ''):
        self._current_image = self.get_background().copy()
        self.draw_dealer_hand()
        self.draw_hands()
        self.draw_status(status)
        return self._current_image.resize((self._current_image.width * 2, self._current_image.height * 2))


def testing_icon():
    url = 'https://cdn.discordapp.com/avatars/180067685986467840/39c1647625215203078dd28d0a3f4860.png?size=1024'
    icon_data = io.BytesIO(requests.get(url, stream=True).content)
    img = Image.open(icon_data)
    mask = Image.new('L', (64, 64), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + mask.size, fill=255)
    del draw
    final = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
    final.putalpha(mask)
    return final


async def get_member_icon(session: 'ClientSession', url: str) -> Image:
    async with session.get(url) as response:
        icon_data = io.BytesIO(await response.read())
    img = Image.open(icon_data)
    mask = Image.new('L', (64, 64), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + mask.size, fill=255)
    del draw
    final = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
    final.putalpha(mask)
    return final

# if __name__ == '__main__':
#     url = 'https://cdn.discordapp.com/avatars/180067685986467840/39c1647625215203078dd28d0a3f4860.png?size=1024'
#     icon_data = io.BytesIO(requests.get(url, stream=True).content)
#     img = Image.open(icon_data)
#     mask = Image.new('L', (64, 64), 0)
#     draw = ImageDraw.Draw(mask)
#     draw.ellipse((0, 0) + mask.size, fill=255)
#     final = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
#     final.putalpha(mask)
#     final.save('icon.png')
