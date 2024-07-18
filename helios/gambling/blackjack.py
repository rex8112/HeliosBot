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
import asyncio
import io
from typing import TYPE_CHECKING, Optional

import discord

from ..member import HeliosMember
from .cards import Hand, Deck, Card
from .image import get_member_icon, BlackjackHandImage, BlackjackImage

if TYPE_CHECKING:
    from PIL import Image


class BlackJack:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel

        self.players: list[HeliosMember] = []
        self.icons: list['Image'] = []
        self.deck: Deck = Deck.new_many(2)
        self.hands: list[list[Hand]] = []
        self.hand_images: list['BlackjackHandImage'] = []
        self.bets: list[list[int]] = []

        self.current_player: int = 0

        self.dealer_icon: 'Image' = None
        self.dealer_hand: Hand = Hand()
        self.dealer_hand_image: Optional['BlackjackHandImage'] = None

        self.message: Optional['discord.Message'] = None
        self.view: Optional['discord.ui.View'] = None

    def reset(self):
        self.players = []
        self.icons = []
        self.deck = Deck.new_many(2)
        self.hands = [Hand()]
        self.bets = []
        self.hand_images = []
        self.dealer_hand = Hand()

    async def update_message(self, state: str):
        img = self.get_image_uploadable(state)
        if self.message:
            await self.message.edit(attachments=[discord.File(img, 'blackjack.png')],
                                    view=self.view)
        else:
            self.message = await self.channel.send(files=[discord.File(img, 'blackjack.png')],
                                                   view=self.view)

    async def add_player(self, player: HeliosMember):
        self.players.append(player)
        self.hands.append([Hand()])
        self.bets.append([0])
        self.icons.append(await get_member_icon(player.bot.get_session(), player.member.display_avatar.url))

    async def remove_player(self, player: HeliosMember):
        index = self.players.index(player)
        self.players.pop(index)
        self.hands.pop(index)
        self.bets.pop(index)
        self.icons.pop(index)

    async def hit(self):
        hand = self.hands[self.current_player][0]
        self.deck.draw_to_hand(hand)
        if hand.get_hand_bj_values() >= 21:
            await self.stand()
        else:
            await self.update_message('Waiting For Player')

    async def stand(self):
        self.current_player += 1
        if self.current_player == len(self.players):
            await self.dealer_play()
        else:
            await self.update_message('Waiting For Player')

    async def dealer_play(self):
        await self.update_message('Dealer Playing')
        await asyncio.sleep(1)
        while self.dealer_hand.get_hand_bj_values() < 17:
            self.deck.draw_to_hand(self.dealer_hand)
            await self.update_message('Dealer Playing')
            await asyncio.sleep(1)
        if self.dealer_hand.get_hand_bj_values() > 21:
            await self.update_message('Dealer Bust')
        else:
            await self.update_message('Dealer Stand')

    def calculate_winnings(self):
        winnings = []
        dealer_value = self.dealer_hand.get_hand_bj_values()
        for i, player in enumerate(self.players):
            player_value = self.hands[i][0].get_hand_bj_values()
            bet = self.bets[i][0]
            amount_won = 0
            if player_value > 21:
                amount_won = 0
            elif dealer_value > 21:
                amount_won = bet * 2
            elif player_value > dealer_value:
                amount_won = bet * 2

            winnings.append(amount_won)
        return winnings

    def generate_hand_images(self):
        self.hand_images = []
        for hands, icon, bets, player in zip(self.hands, self.icons, self.bets, self.players):
            self.hand_images.append(BlackjackHandImage(hands[0], icon, player.member.display_name[:10], bets[0]))
        self.dealer_hand_image = BlackjackHandImage(self.dealer_hand, self.dealer_icon, 'Dealer', '')

    def generate_dealer_image(self):
        self.dealer_icon = get_member_icon(self.players[0].bot.get_session(),
                                           self.players[0].bot.user.display_avatar.url)

    def get_image_uploadable(self, state: str) -> io.BytesIO:
        img = BlackjackImage(self.dealer_hand_image, self.hand_images).get_image(state)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes

    def get_hands(self, player: HeliosMember):
        index = self.players.index(player)
        return self.hands[index]

    def get_bets(self, player: HeliosMember):
        index = self.players.index(player)
        return self.bets[index]

