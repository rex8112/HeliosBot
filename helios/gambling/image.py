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
from typing import Union, TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from pokerkit import Card as PCards

if TYPE_CHECKING:
    from ..member import HeliosMember
    from .cards import Card


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


def get_bj_hand_image(cards: list['Card'], icon: Image, name: str, bet: str, hand_value: str) -> Image:
    card_height = 200
    card_width = 145
    card_gap = -105
    card_spots = 10
    padding = 20
    width = padding + (card_width * card_spots) + (card_gap * (card_spots - 1)) + padding

    icon = icon.resize((64, 64))
    content_height = padding + icon.height + 10 + card_height + padding

    background = Image.new(mode='RGBA', size=(width, content_height), color=(255, 0, 0, 0))
    b_draw = ImageDraw.Draw(background)
    b_draw.rounded_rectangle(((0, 0), background.size), 30, fill='black')

    background.paste(icon, (padding, padding), mask=icon)

    draw = ImageDraw.Draw(background)
    start_x = padding + icon.width + 10
    draw.text((start_x, padding), name, fill='white', font_size=20)
    draw.text((start_x, padding + 30), bet, fill='white', font_size=16)
    draw.text((width - padding, padding), hand_value, fill='white', font_size=36, anchor='rt')

    card_top = background.height - card_height - padding
    x = padding
    for card in cards:
        if card.hidden:
            # card = Image.open('./helios/resources/cards/back.png')
            # background.paste(card, (x, 100), mask=card)
            continue
        else:
            try:
                img = Image.open(f'./helios/resources/cards/{card.short()}.png')
                background.paste(img, (x, card_top), mask=img)
            except FileNotFoundError:
                ...
        x += card_width + card_gap
    return background


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

