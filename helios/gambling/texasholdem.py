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
import logging
from typing import TYPE_CHECKING, Optional
from enum import Enum

import discord
from pokerkit import NoLimitTexasHoldem, State

from .game import Game
from ..colour import Colour

if TYPE_CHECKING:
    from ..server import Server
    from ..member import HeliosMember

logger = logging.getLogger('HeliosLogger.Poker')


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


class TexasHoldEm:
    def __init__(self, server: 'Server', *, buy_in: int):
        self.server = server
        self.buy_in = buy_in
        self.state: Optional[State] = None
        self.phase: Phase = Phase.END
        self.players: list['HeliosMember'] = []

        self._current_players: list['HeliosMember'] = []
        self._stacks: dict['HeliosMember', int] = {}
        self._channel: Optional[discord.TextChannel] = None
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

    async def run_game(self):
        self.evaluate_phase()
        if self.phase == Phase.ANTE_POSTING:
            try:
                while True:
                    self.state.post_ante()
            except ValueError:
                ...
            self.evaluate_phase()
        if self.phase == Phase.BLIND_OR_STRADDLE_POSTING:
            ...

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
        if self.state is None:
            self.phase = Phase.END
        elif self.state.can_post_ante():
            self.phase = Phase.ANTE_POSTING
        elif self.state.can_collect_bets():
            self.phase = Phase.BET_COLLECTION
        elif self.state.can_post_blind_or_straddle():
            self.phase = Phase.BLIND_OR_STRADDLE_POSTING
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
        if self.state is None or self.waiting_for() is None:
            return discord.Embed(
                title='No ones turn',
                colour=Colour.poker_playing()
            )
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

    def get_embeds(self):
        player_embed = self.get_player_embed()
        table_embed = self.get_table_embed()
        playing_embed = self.get_playing_embed()

        return [table_embed, player_embed, playing_embed]
