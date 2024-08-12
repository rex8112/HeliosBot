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
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Callable, Awaitable

import discord

from .cards import Hand, Deck
from .image import get_member_icon, BlackjackHandImage, BlackjackImage, BlackjackHandSplitImage
from ..colour import Colour
from ..database import BlackjackModel
from ..member import HeliosMember
from ..tools.modals import AmountModal
from ..views.generic_views import YesNoView

if TYPE_CHECKING:
    from PIL import Image
    from .manager import GamblingManager

logger = logging.getLogger('HeliosLogger: Blackjack')


def turn_timer(seconds: int) -> Callable[[], Awaitable[None]]:
    async def inner():
        await asyncio.sleep(seconds)

    return inner


# noinspection PyAsyncCall
class Blackjack:
    def __init__(self, manager: 'GamblingManager', channel: discord.TextChannel):
        self.manager = manager
        self.server = self.manager.server
        self.channel = channel

        self.players: list[HeliosMember] = []
        self.icons: list['Image'] = []
        self.deck: Deck = Deck()
        self.hands: list[list[Hand]] = []
        self.hand_images: list['BlackjackHandImage'] = []
        self.bets: list[list[int]] = []

        self.current_player: int = -1
        self.current_hand: int = 0
        self.max_players: int = 8
        self.winnings = []
        self.id = None

        self.dealer_icon: 'Image' = None
        self.dealer_hand: Hand = Hand()
        self.dealer_hand_image: Optional['BlackjackHandImage'] = None

        self.message: Optional['discord.Message'] = None
        self.view: Optional['discord.ui.View'] = None
        self.db_entry: Optional['BlackjackModel'] = None

    def reset(self):
        self.players = []
        self.icons = []
        self.deck = Deck()
        self.hands = [Hand()]
        self.bets = []
        self.hand_images = []
        self.dealer_hand = Hand()

    def to_dict(self):
        return {
            'players': [player.id for player in self.players],
            'hands': [hand[0].to_dict() for hand in self.hands],
            'bets': self.bets,
            'dealer_hand': self.dealer_hand.to_dict(),
            'winnings': self.winnings,
        }

    async def update_message(self, state: str, timer: int = 0):
        img = self.get_image_file(state, timer)
        if self.message:
            await self.message.edit(attachments=[img], view=self.view)
        else:
            self.message = await self.channel.send(files=[img], view=self.view)

    async def add_player(self, player: HeliosMember, bet: int = 0):
        self.players.append(player)
        self.hands.append([Hand()])
        self.bets.append([bet])
        self.icons.append(await get_member_icon(player.bot.get_session(), player.member.display_avatar.url))
        self.generate_hand_images()

    async def remove_player(self, player: HeliosMember):
        index = self.players.index(player)
        self.players.pop(index)
        self.hands.pop(index)
        self.bets.pop(index)
        self.icons.pop(index)
        self.hand_images.pop(index)

    async def start(self):
        await self.generate_dealer_image()
        self.generate_hand_images()
        self.view = BlackjackJoinView(self)
        self.deck.shuffle()
        seconds = 30
        await self.update_message('Waiting For Players to Join', seconds)
        then = datetime.now() + timedelta(seconds=seconds)
        while datetime.now() < then:
            await asyncio.sleep(1)
            seconds -= 1
            if len(self.players) >= self.max_players:
                self.view.stop()
                break
            else:
                await self.update_message('Waiting For Players to Join',
                                          int((then - datetime.now()).total_seconds()))
        if len(self.players) < 1:
            self.view.stop()
            await self.update_message('Not Enough Players')
            await self.message.delete(delay=5)
            return
        try:
            await self.run()
        except Exception as e:
            await self.update_message('Error')
            logger.exception(e)
            if not self.winnings:
                for player in self.players:
                    await player.add_points(sum(self.bets[self.players.index(player)]), 'Helios: Blackjack',
                                            f'{self.id}: Refund')

    async def run(self):
        # Check if players still have enough points
        for player in self.players[:]:
            bet = self.bets[self.players.index(player)][0]
            if bet > player.points:
                await self.remove_player(player)
        if len(self.players) < 1:
            await self.update_message('Not Enough Players')
            await self.message.delete(delay=5)
            return

        # Create Database Entry and set ID
        self.db_entry = await BlackjackModel.create(self.to_dict()['players'])
        self.id = self.db_entry.id

        # Take Bets
        for player in self.players[:]:
            bet = self.bets[self.players.index(player)][0]
            await player.add_points(-bet, 'Helios: Blackjack', f'{self.id}: Bet')

        # Make Board
        self.generate_hand_images()
        self.view = None
        await self.update_message('Drawing Cards')
        await asyncio.sleep(1)

        # Draw Initial Cards
        self.deck.draw_to_hand(self.dealer_hand, hidden=True)
        await self.update_message('Drawing Cards')
        await self.db_entry.async_update(**self.to_dict())
        await asyncio.sleep(0.5)

        for hand in self.hands:
            self.deck.draw_to_hand(hand[0])
            await self.update_message('Drawing Cards')
            await self.db_entry.async_update(**self.to_dict())
            await asyncio.sleep(0.5)

        self.deck.draw_to_hand(self.dealer_hand)
        await self.update_message('Drawing Cards')
        await self.db_entry.async_update(**self.to_dict())
        await asyncio.sleep(0.5)

        for hand in self.hands:
            self.deck.draw_to_hand(hand[0])
            await self.update_message('Drawing Cards')
            await self.db_entry.async_update(**self.to_dict())
            await asyncio.sleep(0.5)

        if self.dealer_hand.get_hand_bj_values(False) in [11, 10]:
            await self.update_message('Dealer Checking for Blackjack')
            await asyncio.sleep(3)

        if self.dealer_hand.get_hand_bj_values() == 21:
            for card in self.dealer_hand.cards:
                card.hidden = False
            self.generate_hand_images()
            await self.update_message('Dealer Blackjack')
            await asyncio.sleep(1)
        else:
            # Player Turns
            self.current_player = 0
            while self.current_player < len(self.players):
                if self.hands[self.current_player][self.current_hand].get_hand_bj_values() >= 21:
                    await self.stand()
                    continue

                self.view = BlackjackView(self)
                await self.update_message('Waiting For Player')
                _, pending = await asyncio.wait([asyncio.create_task(self.view.wait())], timeout=30)
                if pending:
                    self.view.stop()
                    await self.stand()
                    continue
            await self.db_entry.async_update(**self.to_dict())
            self.view = None

            await self.dealer_play()

            await self.update_message('Calculating Winnings')
            await self.db_entry.async_update(**self.to_dict())
            await asyncio.sleep(1)

        self.calculate_winnings()
        for i, player in enumerate(self.players):
            for j, winning in enumerate(self.winnings[i]):
                desc = f'{self.id}: Winnings'
                if j > 0:
                    desc = f'{self.id}: Split Winnings'
                await player.add_points(winning, 'Helios: Blackjack', desc)
            self.manager.add_loss(player, sum(self.bets[i]) - sum(self.winnings[i]))
        await self.update_message('Game Over')
        await self.db_entry.async_update(winnings=self.winnings)
        asyncio.create_task(self.manager.run_blackjack(self.channel))

    async def hit(self):
        hand = self.hands[self.current_player][self.current_hand]
        if len(self.deck.cards) < 1:
            self.deck = Deck()
            self.deck.shuffle()
        self.deck.draw_to_hand(hand)

    async def stand(self):
        if len(self.hands[self.current_player]) > self.current_hand + 1:
            self.current_hand += 1
        else:
            self.current_player += 1
            self.current_hand = 0

    def is_soft_seventeen(self):
        if (self.dealer_hand.get_hand_bj_values() == 17
                and self.dealer_hand.get_hand_bj_values(suppress_eleven=True) < 17):
            soft_seventeen = True
        else:
            soft_seventeen = False
        return soft_seventeen

    async def dealer_play(self):
        for card in self.dealer_hand.cards:
            card.hidden = False
        self.generate_hand_images()
        await self.update_message('Dealer Playing')
        await asyncio.sleep(1)

        while self.is_soft_seventeen() or self.dealer_hand.get_hand_bj_values() < 17:
            if len(self.deck.cards) < 1:
                self.deck = Deck()
                self.deck.shuffle()
            self.deck.draw_to_hand(self.dealer_hand)
            await self.update_message('Dealer Playing')
            await asyncio.sleep(1)
        if self.dealer_hand.get_hand_bj_values() > 21:
            await self.update_message('Dealer Busts')
        else:
            await self.update_message('Dealer Stands')
        await asyncio.sleep(1)

    def calculate_winnings(self):
        winnings = []
        dealer_value = self.dealer_hand.get_hand_bj_values()
        for i, player in enumerate(self.players):
            amount_won = []
            for j, hand in enumerate(self.hands[i]):
                player_value = hand.get_hand_bj_values()
                bet = self.bets[i][j]
                won = 0
                if len(self.dealer_hand.cards) == 2 and dealer_value == 21:
                    if len(hand.cards) == 2 and player_value == 21:
                        won = bet
                    else:
                        won = 0
                elif len(hand.cards) == 2 and player_value == 21:
                    won = int(bet * 2.5)
                elif player_value > 21:
                    won = 0
                elif dealer_value > 21:
                    won = bet * 2
                elif player_value == dealer_value == 21:
                    won = int(bet * 1.5)
                elif player_value == dealer_value:
                    won = bet
                elif player_value > dealer_value:
                    won = bet * 2
                amount_won.append(won)
            winnings.append(amount_won)
        self.winnings = winnings
        return winnings

    def generate_hand_images(self):
        self.hand_images = []
        for hands, icon, bets, player in zip(self.hands, self.icons, self.bets, self.players):
            if len(hands) > 1:
                self.hand_images.append(BlackjackHandSplitImage(hands, icon, player.member.display_name[:10], bets))
            else:
                self.hand_images.append(BlackjackHandImage(hands[0], icon, player.member.display_name[:10], bets[0]))
        self.dealer_hand_image = BlackjackHandImage(self.dealer_hand, self.dealer_icon, 'Dealer', 0)

    async def generate_dealer_image(self):
        self.dealer_icon = await get_member_icon(self.server.bot.get_session(),
                                                 self.server.bot.user.display_avatar.url)

    def get_image_file(self, state: str, timer: int) -> discord.File:
        img = BlackjackImage(self.dealer_hand_image, self.hand_images, self.current_player, self.current_hand,
                             self.id if self.id else 0, self.winnings).get_image(state, timer)
        with io.BytesIO() as img_bytes:
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            file = discord.File(img_bytes, 'blackjack.png')
        return file

    def get_hands(self, player: HeliosMember):
        index = self.players.index(player)
        return self.hands[index]

    def get_bets(self, player: HeliosMember):
        index = self.players.index(player)
        return self.bets[index]


class BlackjackView(discord.ui.View):
    def __init__(self, blackjack: Blackjack):
        super().__init__(timeout=30)
        self.blackjack = blackjack
        self.check_buttons()

    def check_buttons(self):
        player = self.blackjack.players[self.blackjack.current_player]
        hands = self.blackjack.hands[self.blackjack.current_player]
        hand = hands[self.blackjack.current_hand]
        if len(hand.cards) > 2 or (len(hands) > 1 and len(hand.cards) > 1):
            self.remove_item(self.double_down)
            self.remove_item(self.split)
        elif player.points < self.blackjack.bets[self.blackjack.current_player][self.blackjack.current_hand]:
            self.double_down.disabled = True
            self.split.disabled = True
        elif len(hands) > 1 or hand.cards[0].bj_value() != hand.cards[1].bj_value():
            self.remove_item(self.split)

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.blackjack.players[self.blackjack.current_player]
        if player.member != interaction.user:
            await interaction.response.send_message('It is not your turn.', ephemeral=True)
            return
        await interaction.response.defer()
        await self.blackjack.hit()
        self.stop()

    @discord.ui.button(label='Stand', style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.blackjack.players[self.blackjack.current_player]
        if player.member != interaction.user:
            await interaction.response.send_message('It is not your turn.', ephemeral=True)
            return
        await interaction.response.defer()
        await self.blackjack.stand()
        self.stop()

    @discord.ui.button(label='Double Down', style=discord.ButtonStyle.blurple)
    async def double_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.blackjack.players[self.blackjack.current_player]
        if player.member != interaction.user:
            await interaction.response.send_message('It is not your turn.', ephemeral=True)
            return
        hand = self.blackjack.hands[self.blackjack.current_player][self.blackjack.current_hand]
        if len(hand.cards) > 2:
            await interaction.response.send_message('You can only double down on your first turn.', ephemeral=True)
            return
        if player.points < self.blackjack.bets[self.blackjack.current_player][self.blackjack.current_hand]:
            await interaction.response.send_message('You do not have enough points to double down.', ephemeral=True)
            return
        await interaction.response.defer()
        await player.add_points(-self.blackjack.bets[self.blackjack.current_player][self.blackjack.current_hand],
                                'Helios: Blackjack', f'{self.blackjack.id}: Double Down')
        hand_num = self.blackjack.current_hand
        player_num = self.blackjack.current_player
        self.blackjack.bets[player_num][hand_num] *= 2
        hand_image = self.blackjack.hand_images[player_num]
        if isinstance(hand_image, BlackjackHandSplitImage):
            hand_image.bets[hand_num] = self.blackjack.bets[player_num][hand_num]
        else:
            hand_image.bet = self.blackjack.bets[player_num][hand_num]
        hand_image.get_image(redraw=True)
        await self.blackjack.hit()
        await self.blackjack.stand()
        self.stop()

    @discord.ui.button(label='Split', style=discord.ButtonStyle.blurple)
    async def split(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.blackjack.players[self.blackjack.current_player]
        if player.member != interaction.user:
            await interaction.response.send_message('It is not your turn.', ephemeral=True)
            return
        hand = self.blackjack.hands[self.blackjack.current_player][0]
        if len(hand.cards) > 2:
            await interaction.response.send_message('You can only split on your first turn.', ephemeral=True)
            return
        if player.points < self.blackjack.bets[self.blackjack.current_player][0]:
            await interaction.response.send_message('You do not have enough points to split.', ephemeral=True)
            return
        if hand.cards[0].bj_value() != hand.cards[1].bj_value():
            await interaction.response.send_message('You can only split if your first two cards are the same.',
                                                    ephemeral=True)
            return
        await interaction.response.defer()
        await player.add_points(-self.blackjack.bets[self.blackjack.current_player][0], 'Helios: Blackjack',
                                f'{self.blackjack.id}: Split Bet')
        self.blackjack.bets[self.blackjack.current_player].append(self.blackjack.bets[self.blackjack.current_player][0])
        new_hand = Hand()
        new_hand.add_card(hand.cards.pop())
        self.blackjack.hands[self.blackjack.current_player].append(new_hand)
        self.blackjack.generate_hand_images()
        await self.blackjack.update_message('Splitting')
        await asyncio.sleep(0.5)
        for hand in self.blackjack.hands[self.blackjack.current_player]:
            self.blackjack.deck.draw_to_hand(hand)
            await self.blackjack.update_message('Drawing Cards')
            await asyncio.sleep(0.5)
        self.stop()


rules_embed = discord.Embed(
    title='Blackjack Rules',
    colour=Colour.helios(),
    description='## Goal\n'
                'The goal of blackjack is to beat the dealer\'s hand without going over 21.\n'
                '## Bets\n'
                'Each player must bet at least 1 point to play, there is no maximum.\n'
                'Bets are taken once the game starts.\n'
                '## Game Play\n'
                '1. Players are dealt two cards face up.\n'
                '2. The dealer is dealt one card face up and one card face down.\n'
                '3. Players take turns hitting or standing.\n'
                '4. The dealer plays last.\n'
                '5. The dealer must hit until they have a hard 17 or higher.\n'
                '6. Players who have a higher hand than the dealer, without going over 21 win.\n'
                '## Winning\n'
                '1. Players who win receive 2x their bet (keep in mind you lose your bet to start playing, so your net '
                'winnings is your bet amount.)\n'
                '2. Players who get a natural blackjack (21 with two cards) receive 2.5x their bet.\n'
                '3. Players who tie with the dealer get their bet back.\n'
                '4. Players who lose get nothing.\n'
                '5. If the dealer gets a natural blackjack, all players lose except those who also have a natural '
                'blackjack, they tie.\n'
                '6. If the dealer and player both have blackjack from hitting, the player wins 1.5x their bet.\n'
                '## Moves\n'
                '1. **Hit** - Take another card.\n'
                '2. **Stand** - Keep your current hand.\n'
                '3. **Double Down** - Double your bet and take one more card only.\n'
                '4. **Split** - If your first two cards are the same, you can split them into two hands, placing an '
                'equal bet on the second hand, and play those hands separately.\n'
                '## Time\n'
                'Players have 30 seconds to make a move, if they do not make a move in time, they will stand.\n'
                '## Refunds\n'
                'If the game errors out, and shows error on the table, all players will be refunded their bets '
                'automatically. '
                'However, if the game ends due to disconnection, please report the game to my owner for a refund. '
                '(Do not forget the game ID number.)\n'
                '## Notes\n'
                'Helios is not responsible for any stress or loss of sleep due to playing blackjack.\n'
                '[If you have a gambling problem, please seek help.](<https://www.youtube.com/watch?v=dQw4w9WgXcQ>)\n'
)


class BlackjackJoinView(discord.ui.View):
    def __init__(self, blackjack: Blackjack):
        super().__init__(timeout=120)
        self.blackjack = blackjack

    @discord.ui.button(label='Join', style=discord.ButtonStyle.primary)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = self.blackjack.server.members.get(interaction.user.id)
        if member in self.blackjack.players:
            await interaction.response.send_message('You are already in the game.', ephemeral=True)
            return
        if len(self.blackjack.players) >= self.blackjack.max_players:
            await interaction.response.send_message('The game is full.', ephemeral=True)
            return
        modal = AmountModal(thinking=True)
        await interaction.response.send_modal(modal)
        if await modal.wait():
            return
        interaction = modal.last_interaction
        if modal.amount_selected <= 0:
            await interaction.followup.send(
                content=f'You must bet at least 1 {member.server.points_name.capitalize()}.')
            return
        amount = modal.amount_selected
        if amount > member.points:
            await interaction.followup.send(
                content=f'You do not have enough {member.server.points_name.capitalize()}s.')
            return

        if self.blackjack.manager.needs_help(member):
            dealer_cards = [self.blackjack.deck.cards[-1], self.blackjack.deck.cards[-len(self.blackjack.players) - 3]]
            dealer_hand = Hand()
            dealer_hand.add_cards(dealer_cards)
            if dealer_hand.get_hand_bj_values() == 21:
                await interaction.followup.send(f'Hey, you have a pretty rough loss streak. '
                                                f'I strongly recommend not betting on this game.')
                self.blackjack.manager.helped(member)
                return
        if amount > member.points * 0.1:
            view = YesNoView(interaction.user, timeout=15, thinking=True, ephemeral=True)
            await interaction.followup.send(f'Are you sure you want to bet '
                                            f'**{amount:,}** {member.server.points_name}? This is '
                                            f'**{amount / member.points:.2%}** of your points.', view=view)
            if await view.wait() or not view.value:
                await interaction.edit_original_response(view=None)
                if view.last_interaction:
                    await view.last_interaction.followup.send(content='You have not joined the game.')
                return
            else:
                await interaction.edit_original_response(view=None)
            interaction = view.last_interaction

        if self.blackjack.id is not None:
            await interaction.followup.send(content='The game has already started.')
            return

        await self.blackjack.add_player(member, amount)
        await interaction.followup.send(content=f'You have joined the game with a bet of {amount} '
                                                f'{member.server.points_name.capitalize()}.')

    @discord.ui.button(label='Rules', style=discord.ButtonStyle.secondary)
    async def rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=rules_embed, ephemeral=True)
