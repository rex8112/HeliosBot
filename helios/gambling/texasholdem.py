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
import logging
from typing import TYPE_CHECKING, Optional
from enum import Enum

import discord
from pokerkit import NoLimitTexasHoldem, State

from .image import get_card_images
from .game import Game
from ..colour import Colour

if TYPE_CHECKING:
    from ..server import Server
    from ..member import HeliosMember

logger = logging.getLogger('HeliosLogger.Poker')


def and_join(s: list[str]):
    if len(s) > 1:
        last = s[-1]
        first = ', '.join(s[:-1])
        names = f'{first}, and {last}'
    else:
        names = s[0]
    return names


class Phase(Enum):
    ANTE_POSTING = 0
    BET_COLLECTION = 1
    BLIND_OR_STRADDLE_POSTING = 2
    DEALING = 3
    BETTING = 4
    SHOWDOWN = 5
    HAND_KILLING = 6
    CHIPS_PUSHING = 7
    CHIPS_PULLING = 8
    END = 9
    BURN_CARD = 10


class TexasHoldEm:
    MAX_PLAYERS = 10

    def __init__(self, server: 'Server', *, buy_in: int):
        self.server = server
        self.buy_in = buy_in
        self.state: Optional[State] = None
        self.phase: Phase = Phase.END
        self.players: list['HeliosMember'] = []

        self._current_players: list['HeliosMember'] = []
        self._stacks: dict['HeliosMember', int] = {}
        self._channel: Optional[discord.TextChannel] = None
        self._message: Optional[discord.Message] = None
        self._delete_action = None

    @property
    def big_blind(self):
        if self.buy_in > 500:
            return int(self.buy_in / 500) * 10
        else:
            return int(self.buy_in / 50)

    @property
    def small_blind(self):
        bb = self.big_blind
        if bb > 5:
            return int(bb / 2)
        else:
            return bb

    async def create_table(self):
        self._channel = self.server.guild.create_text_channel(f'{self.buy_in}-texasholdem')
        self._delete_action = await self.server.bot.event_manager.add_action('on_start', self._channel, 'delete_channel')

    async def delete_table(self):
        if self._channel is not None:
            try:
                await self._channel.delete()
            except (discord.Forbidden, discord.NotFound) as e:
                logger.warning(f'Failed to delete channel: {e}')
        self._channel = None
        if self._delete_action is not None:
            await self.server.bot.event_manager.delete_action(self._delete_action)
        self._delete_action = None

    async def update_message(self, view=None):
        kwargs = {'embeds': self.get_embeds()}
        if view is None:
            ...

        if self._message is None:
            self._message = await self._channel.send(**kwargs)
        else:
            await self._message.edit(embeds=kwargs.get('embeds'), view=kwargs.get('view'))

    async def run_game(self):
        self.evaluate_phase()
        while self.phase != Phase.END:
            if self.phase == Phase.ANTE_POSTING:
                self.state.post_ante()
            elif self.phase == Phase.BLIND_OR_STRADDLE_POSTING:
                self.state.post_blind_or_straddle()
            elif self.phase == Phase.BURN_CARD:
                self.state.burn_card()
            elif self.phase == Phase.HAND_KILLING:
                self.state.kill_hand()
            elif self.phase == Phase.CHIPS_PUSHING:
                self.state.push_chips()
            elif self.phase == Phase.CHIPS_PULLING:
                self.state.pull_chips()
            elif self.phase == Phase.DEALING:
                await self.update_message()
                while self.state.can_deal_hole():
                    self.state.deal_hole()
                while self.state.can_deal_board():
                    self.state.deal_board()
                await asyncio.sleep(2)
            elif self.phase == Phase.BETTING:
                while self.state.can_check_or_call() or self.state.can_fold():
                    if self.waiting_for() in self.players:
                        view = BettingView(self)
                        await self.update_message(view)
                        await view.wait()
                    else:
                        if self.state.checking_or_calling_amount == 0:
                            self.state.check_or_call()
                        else:
                            self.state.fold()
            elif self.phase == Phase.SHOWDOWN:
                await self.update_message()
                await asyncio.sleep(2)
                messages = []
                while self.state.can_show_or_muck_hole_cards():
                    res = self.state.show_or_muck_hole_cards(True)
                    messages.append(await self.show_cards(self._current_players[res.player_index],
                                                          tuple(str(x) for x in res.hole_cards)))
                    await asyncio.sleep(1)
                await asyncio.sleep(1)
                messages.append(await self.show_winners())
                await asyncio.sleep(3)
                tasks = (x.delete() for x in messages)
                await asyncio.gather(*tasks, return_exceptions=True)

            self.evaluate_phase()

    async def start_game(self):
        self.create_state()

    async def end_game(self):
        for i, player in enumerate(self._current_players):
            self._stacks[player] = self.state.stacks[i]
            if player not in self.players:
                stack = self._stacks[player]
                del self._stacks[player]
                if stack > 0:
                    await player.add_points(stack, 'Helios', 'Texas Hold \'Em Payout')

    async def show_cards(self, member: 'HeliosMember', cards: tuple[str, ...]):
        embed = discord.Embed(
            title=f'{member}\'s Cards',
            colour=Colour.poker_table()
        )
        img = discord.File(get_card_images(cards, 2), 'hand.png', description=str(cards))
        embed.set_image(url='attachment://hand.png')
        return await self._channel.send(embed=embed, file=img)

    async def show_winners(self):
        pots = list(self.state.pots)
        main = pots[0]
        winners = list(self._current_players[x] for x in main.player_indices)
        names = and_join(list(str(x) for x in winners))
        embed = discord.Embed(
            title=f'{names} Win the Pot!',
            colour=Colour.poker_table(),
            description=f'{main.amount:,} in the Pot!'
        )
        for pot in pots[1:]:
            winners = list(self._current_players[x] for x in pot.player_indices)
            names = and_join(list(str(x) for x in winners))
            embed.add_field(name='Side Pot', value=f'Winners: **{names}**\nAmount: {pot.amount:,}')
        return await self._channel.send(embed=embed)

    def create_state(self):
        self._current_players = self.players.copy()
        stacks = [self._stacks[x] for x in self._current_players]
        self.state = NoLimitTexasHoldem.create_state(
            (),
            False,
            0,
            (self.big_blind, self.small_blind),
            int(self.buy_in * 0.01),
            stacks,
            len(self._current_players)
        )
        self.evaluate_phase()

    def waiting_for(self):
        if self.state is None:
            return None
        index = self.state.actor_index
        if index is None:
            index = self.state.showdown_index
        return self._current_players[index]

    def waiting_for_index(self):
        if self.state is None:
            return None
        index = self.state.actor_index
        if index is None:
            index = self.state.showdown_index
        return index

    def evaluate_phase(self):
        if self.state is None or not self.state.status:
            self.phase = Phase.END
        elif self.state.can_post_ante():
            self.phase = Phase.ANTE_POSTING
        elif self.state.can_collect_bets():
            self.phase = Phase.BET_COLLECTION
        elif self.state.can_post_blind_or_straddle():
            self.phase = Phase.BLIND_OR_STRADDLE_POSTING
        elif self.state.can_burn_card():
            self.phase = Phase.BURN_CARD
        elif self.state.can_deal_hole() or self.state.can_deal_board():
            self.phase = Phase.DEALING
        elif self.state.can_check_or_call():
            self.phase = Phase.BETTING
        elif self.state.can_show_or_muck_hole_cards():
            self.phase = Phase.SHOWDOWN
        elif self.state.can_kill_hand():
            self.phase = Phase.HAND_KILLING
        elif self.state.can_push_chips():
            self.phase = Phase.CHIPS_PUSHING
        elif self.state.can_pull_chips():
            self.phase = Phase.CHIPS_PULLING
        else:
            raise ValueError('Could not determine phase.')

    def get_player_embed(self):
        embed = discord.Embed(
            title='Players',
            colour=Colour.poker_players()
        )
        if self.state is None:
            embed.description = 'No Game Running'
            return embed

        for i, player in enumerate(self._current_players):
            stack = self.state.stacks[i]
            embed.add_field(
                name=player.member.display_name,
                value=f'Stack: {stack:,}',
                inline=True
            )
        return embed

    def get_table_embed(self, river: bool = False, /):
        embed = discord.Embed(
            title=f'{self.buy_in:,} {self.server.points_name.capitalize()} Texas Hold \'Em',
            colour=Colour.poker_table(),
            description=f'Buy In: {self.buy_in:,}\nBig Blind: {self.big_blind:,}\nSmall Blind: {self.small_blind:,}'
        )
        if river:
            embed.set_image(url='attachment://river.png')
        else:
            embed.set_image(url=None)
        return embed

    def get_playing_embed(self):
        if self.state is None:
            return discord.Embed(
                title='No ones turn',
                colour=Colour.poker_playing()
            )
        if self.phase == Phase.DEALING:
            embed = discord.Embed(
                title='Dealing Cards',
                colour=Colour.poker_playing()
            )
            return embed
        if self.phase == Phase.SHOWDOWN:
            embed = discord.Embed(
                title='Showdown',
                colour=Colour.poker_playing(),
                description='Revealing Cards...'
            )
            return embed
        current = self.waiting_for()
        embed = discord.Embed(
            title=f'Current Turn: {current.member.display_name}',
            colour=Colour.poker_playing()
        )
        embed.set_thumbnail(url=current.member.display_avatar.url)
        if self.phase == Phase.BETTING:
            current_bet = self.state.bets[self.waiting_for_index()]
            # min_bet = self.state.min_completion_betting_or_raising_to_amount
            # max_bet = self.state.max_completion_betting_or_raising_to_amount
            call_amt = self.state.checking_or_calling_amount
            embed.description = f'Currently Bet: {current_bet:,}\nCall Amount: {call_amt:,}'
        elif self.phase == Phase.SHOWDOWN:
            embed.description = 'Show or Muck?'
        return embed

    def get_embeds(self):
        player_embed = self.get_player_embed()
        table_embed = self.get_table_embed()
        playing_embed = self.get_playing_embed()

        return [table_embed, player_embed, playing_embed]


class BettingView(discord.ui.View):
    def __init__(self, game: TexasHoldEm, *, timeout=30):
        self.game = game
        self.state = game.state
        super().__init__(timeout=timeout)

        self.update_buttons()

    def update_buttons(self):
        self.low_bet.label = self.state.min_completion_betting_or_raising_to_amount
        self.double_bet.label = self.state.min_completion_betting_or_raising_to_amount * 2
        self.max_bet.label = self.state.max_completion_betting_or_raising_to_amount
        self.fold_button.disabled = not self.state.can_fold()

    @discord.ui.button(label='low', style=discord.ButtonStyle.gray)
    async def low_bet(self, interaction: discord.Interaction, _):
        amt = self.state.min_completion_betting_or_raising_to_amount

    @discord.ui.button(label='double', style=discord.ButtonStyle.gray)
    async def double_bet(self, interaction: discord.Interaction, _):
        amt = self.state.min_completion_betting_or_raising_to_amount * 2

    @discord.ui.button(label='max', style=discord.ButtonStyle.gray)
    async def max_bet(self, interaction: discord.Interaction, _):
        amt = self.state.max_completion_betting_or_raising_to_amount

    @discord.ui.button(label='Custom', style=discord.ButtonStyle.gray)
    async def custom_bet(self, interaction: discord.Interaction, _):
        ...

    @discord.ui.button(label='Check/Call', style=discord.ButtonStyle.green, row=1)
    async def check_button(self, interaction: discord.Interaction, _):
        ...

    @discord.ui.button(label='Fold', style=discord.ButtonStyle.red, row=1)
    async def fold_button(self, interaction: discord.Interaction, _):
        ...


