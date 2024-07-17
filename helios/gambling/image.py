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
import requests
from typing import Union, TYPE_CHECKING, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageOps, ImageFont
from pokerkit import Card as PCards

if TYPE_CHECKING:
    from ..member import HeliosMember
    from .cards import Card, Hand


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
    def __init__(self, hand: 'Hand', icon: 'Image', name: str, bet: str):
        self.hand = hand
        self.icon: Image = icon.copy().resize((64, 64))
        self.name = name
        self.bet = bet

        self.padding = 20
        self.card_spots = 7
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

    def get_background(self) -> Image:
        if not self._background:
            background = Image.new(mode='RGBA', size=(self.get_width(), self.get_height()), color=(255, 0, 0, 0))
            draw = ImageDraw.Draw(background)
            draw.rounded_rectangle(((0, 0), background.size), 32, fill='black')
            background.paste(self.icon, (self.padding, self.padding), mask=self.icon)

            start_x = self.padding + self.icon.width + 10
            draw.text((start_x, self.padding), self.name, fill='white', font_size=20)
            draw.text((start_x, self.padding + 30), self.bet, fill='white', font_size=16)

            self._background = background
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

    def draw_turn(self) -> Image:
        if self._current_image is None:
            raise ValueError('No current image to draw cards on.')
        img = self._current_image.copy()
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(((0, 0), img.size), 32, outline='green', width=5)
        return img

    def draw_cards(self, cards: list['Card']):
        if self._current_image is None:
            raise ValueError('No current image to draw cards on.')
        x = self.padding + (len(self._currently_shown_cards) * (self.card_width + self.card_gap))
        card_top = self._current_image.height - self.card_height - self.padding
        for card in cards:
            if card.hidden:
                # card = Image.open('./helios/resources/cards/back.png')
                # background.paste(card, (x, 100), mask=card)
                continue
            else:
                try:
                    img = Image.open(f'./helios/resources/cards/{card.short()}.png')
                    self._current_image.paste(img, (x, card_top), mask=img)
                except FileNotFoundError:
                    ...
            x += self.card_width + self.card_gap
        if len(cards):
            self.draw_hand_value()

    def draw_hand_value(self):
        font = ImageFont.load_default(36)
        draw = ImageDraw.Draw(self._current_image)
        bbox = font.getbbox('32')

        draw.rectangle(((self._current_image.width - self.padding - bbox[2], self.padding),
                        (self._current_image.width - self.padding, self.padding + bbox[3])),
                       fill='black')
        hand_value = self.hand.get_hand_bj_values()
        draw.text((self._current_image.width - self.padding, self.padding), str(hand_value), fill='white',
                  font_size=36, anchor='rt')

    def get_image(self, is_turn: bool = False) -> Image:
        diff = self.get_diff()

        if self._current_image is None or diff is None:
            self._current_image = self.get_background().copy()
            self._currently_shown_cards = []
            self.draw_cards(self.hand.cards)
        else:
            self.draw_cards(diff)
        self._currently_shown_cards = self.hand.cards.copy()

        if is_turn:
            return self.draw_turn()

        return self._current_image


def testing_icon():
    url = 'https://cdn.discordapp.com/avatars/180067685986467840/39c1647625215203078dd28d0a3f4860.png?size=1024'
    icon_data = io.BytesIO(requests.get(url, stream=True).content)
    img = Image.open(icon_data)
    mask = Image.new('L', (64, 64), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + mask.size, fill=255)
    final = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
    final.putalpha(mask)
    return final


async def get_member_icon(member: 'HeliosMember') -> Image:
    url = member.member.display_avatar.url
    session = member.bot.get_session()
    async with session.get(url) as response:
        icon_data = io.BytesIO(await response.read())
    img = Image.open(icon_data)
    mask = Image.new('L', (64, 64), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + mask.size, fill=255)
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

