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
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Optional, Union, Any

import discord
from pokerkit import NoLimitTexasHoldem, State, Hand, Card, ChipsPushing, Folding, CheckingOrCalling, \
    CompletionBettingOrRaisingTo

from .image import get_card_images
from ..colour import Colour
from ..tools.modals import AmountModal

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


class Player:
    def __init__(self, member: 'HeliosMember', stack: int):
        self.member = member
        self.player_index = None
        self.stack = stack
        self.left = False
        self.idle = False

    def __hash__(self):
        return self.member.__hash__()


def get_winners(players: list[Player], hands: list[Hand]):
    index_to_remove = []
    for i, hand in enumerate(hands):
        if hand is None:
            index_to_remove.append(i)
    for i in reversed(index_to_remove):
        del players[i]
        del hands[i]
    top = max(hands)
    winners = [x for x, y in zip(players, hands) if y == top]
    return winners


class TexasHoldEm:
    MAX_PLAYERS = 10

    def __init__(self, server: 'Server', *, buy_in: int):
        self.server = server
        self.buy_in = buy_in
        self.state: Optional[State] = None
        self.phase: Phase = Phase.END
        self.players: dict['HeliosMember', Player] = {}

        self._current_players: list[Player] = []
        self._channel: Optional[discord.TextChannel] = None
        self._control_message: Optional[discord.Message] = None
        self._control_view: Optional[TableView] = None
        self._message: Optional[discord.Message] = None
        self._last_game_time: datetime = datetime.now().astimezone()
        self._delete_action = None
        self._ending = False
        self._hands = []
        self._last_action = ''

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
        overwrites = {
            self.server.guild.default_role: discord.PermissionOverwrite(send_messages=False),
            self.server.me: discord.PermissionOverwrite(send_messages=True)
        }
        category = self.server.settings.gambling_category.value
        self._channel = await category.create_text_channel(f'{self.buy_in}-texasholdem', overwrites=overwrites)
        self._delete_action = await self.server.bot.event_manager.add_action('on_start', self._channel, 'delete_channel')
        self._control_message = await self._channel.send(embed=self.get_player_embed(), view=TableView(self))

    async def delete_table(self):
        self._ending = True
        if self._channel is not None:
            try:
                await self._channel.delete()
            except (discord.Forbidden, discord.NotFound) as e:
                logger.warning(f'Failed to delete channel: {e}')
        self._channel = None
        if self._delete_action is not None:
            await self.server.bot.event_manager.delete_action(self._delete_action)
        self._delete_action = None

    async def update_message(self, view=None, timer: Optional[datetime] = None):
        kwargs = {'embeds': self.get_embeds(timer=timer)}
        if view is not None:
            kwargs['view'] = view

        if self.state is not None and self.state.board_cards:
            img = discord.File(get_card_images(tuple(self.state.board_cards), 5), 'river.png')
            kwargs['files'] = [img]

        if self._message is None:
            self._message = await self._channel.send(**kwargs)
        else:
            await self._message.edit(embeds=kwargs.get('embeds'), view=kwargs.get('view'),
                                     attachments=kwargs.get('files', []))
        await self.update_control_message()

    async def update_control_message(self, view=None):
        kwargs = {'embeds': [self.get_player_embed()]}
        if view is None:
            view = TableView(self) if self._control_view is None else self._control_view
        kwargs['view'] = view
        self._control_view = view

        if self._control_message is None:
            self._control_message = await self._channel.send(**kwargs)
        else:
            await self._control_message.edit(embeds=kwargs.get('embeds'), view=kwargs.get('view'))

    def process_action(self, action: Any):
        if isinstance(action, Folding):
            self._last_action = f'{self._current_players[action.player_index].member} **folded**.'
        elif isinstance(action, CheckingOrCalling):
            a_string = 'checked' if action.amount == 0 else 'called'
            self._last_action = f'{self._current_players[action.player_index].member} **{a_string}**.'
        elif isinstance(action, CompletionBettingOrRaisingTo):
            self._last_action = f'{self._current_players[action.player_index].member} raised **{action.amount:,}**.'
        elif isinstance(action, str):
            self._last_action = action

    def start(self):
        asyncio.create_task(self.run_task())

    async def run_task(self):
        while not self._ending:
            try:
                if self._channel is None:
                    await self.create_table()
                    await self.update_message()
                await asyncio.sleep(15)
                if len(self.players) > 1:
                    await self.start_game()
                    await self.run_game()
                    await self.end_game()
                    await self.update_message()
                if self._last_game_time < datetime.now().astimezone() - timedelta(minutes=5):
                    for player in list(self.players.keys()):
                        await self.withdraw(player)
                    await self.delete_table()
            except discord.NotFound as e:
                logger.error(f'Channel not found: {e}', exc_info=True)
                for player in self.players.keys():
                    await self.withdraw(player)
                await self.delete_table()
            except Exception as e:
                logger.error(e, exc_info=True)

    async def run_game(self):
        self.evaluate_phase()
        messages = []
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
                # Game over, push chips and show winners
                await self.update_message()
                await asyncio.sleep(2)
                messages.append(await self.show_winners(self.state.push_chips()))
                await asyncio.sleep(5)
            elif self.phase == Phase.CHIPS_PULLING:
                res = self.state.pull_chips()
                player = self._current_players[res.player_index]
                player.stack += res.amount
            elif self.phase == Phase.DEALING:
                await self.update_message()
                while self.state.can_deal_hole():
                    self.state.deal_hole()
                while self.state.can_deal_board():
                    self.state.deal_board()
                await asyncio.sleep(2)
            elif self.phase == Phase.BETTING:
                await self.do_betting()
            elif self.phase == Phase.SHOWDOWN:
                # No more betting, show cards
                await self.update_message()
                await asyncio.sleep(2)
                while self.state.can_show_or_muck_hole_cards():
                    res = self.state.show_or_muck_hole_cards(True)
                    messages.append(await self.show_cards(self._current_players[res.player_index],
                                                          tuple(res.hole_cards)))
                    await asyncio.sleep(1)
                self._hands = list(self.state.get_up_hands(0))

            self.evaluate_phase()
        tasks = (x.delete() for x in messages)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def do_betting(self):
        while self.state.can_check_or_call() or self.state.can_fold():
            if not self.waiting_for().left:
                player = self.waiting_for()
                view = BettingView(self, timeout=45)
                timer = datetime.now().astimezone() + timedelta(seconds=30)
                await self.update_message(view, timer=timer)
                tasks = (asyncio.create_task(view.wait()), asyncio.create_task(asyncio.sleep(30)))
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                if not view.is_finished():
                    view.stop()
                    self.skip_turn()
                    player.idle = True
                else:
                    player.idle = False
            else:
                self.skip_turn()
        while self.state.can_collect_bets():
            res = self.state.collect_bets()
            bets = res.bets
            for i, bet in enumerate(bets):
                player = self._current_players[i]
                player.stack -= bet

    def skip_turn(self):
        if self.state.checking_or_calling_amount == 0:
            self.state.check_or_call()
        else:
            self.state.fold()

    async def start_game(self):
        self.build_current_players()
        self.create_state()

    async def end_game(self):
        self._last_game_time = datetime.now().astimezone()
        self._hands = []
        for i, player in enumerate(self._current_players):
            player.player_index = None
            if player.left or player.stack == 0 or player.idle:
                await self.remove_player(player)
        self.state = None
        await self.update_message()

    async def remove_player(self, member: Player):
        del self.players[member.member]
        stack = member.stack
        if stack > 0:
            # await member.member.add_points(stack, 'Helios', 'Texas Hold \'Em Payout')
            ...

    async def withdraw(self, member: 'HeliosMember'):
        if member in self.players:
            player = self.players[member]
            player.left = True
            if self.phase == Phase.END:
                await self.remove_player(player)

    async def add_player(self, member: 'HeliosMember'):
        if member in self.players:
            raise ValueError('Player already in game.')
        if len(self.players) >= self.MAX_PLAYERS:
            raise ValueError('Game is full.')
        player = Player(member, self.buy_in)
        self.players[member] = player
        # await member.add_points(-self.buy_in, 'Helios', 'Texas Hold \'Em Buy In')

    async def show_cards(self, member: Player, cards: tuple[Union[str, Card], ...]):
        embed = discord.Embed(
            title=f'{member.member}\'s Cards',
            colour=Colour.poker_table(),
            description=str(self.state.get_hand(self._current_players.index(member), 0))
        )
        img = discord.File(get_card_images(cards, 5), 'hand.png', description=str(cards))
        embed.set_image(url='attachment://hand.png')
        ret = await self._channel.send(embed=embed, file=img)
        img.close()
        return ret

    async def show_winners(self, push: ChipsPushing):
        amounts = list(push.amounts)
        winners: list[tuple[Player, int]] = list(zip(self._current_players, amounts))
        winners.sort(key=lambda x: x[1], reverse=True)
        winner_strings = []
        for winner, amount in winners:
            if amount > 0:
                winner_strings.append(f'{winner.member} won **{amount:,}**!')
        embed = discord.Embed(
            title=f'Winners!',
            colour=Colour.poker_table(),
            description='\n'.join(winner_strings)
        )
        return await self._channel.send(embed=embed)

    def build_current_players(self):
        self._current_players.clear()
        for i, player in enumerate(self.players.values()):
            player.player_index = i
            self._current_players.append(player)

    def create_state(self):
        stacks = [x.stack for x in self._current_players]
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
        if index is None:
            return None
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

        for i, player in enumerate(self.players.values()):
            stack = self.state.stacks[i] if self.phase != Phase.END and player in self._current_players else player.stack
            if player.left:
                value = f'**Left**\n'
            elif player not in self._current_players:
                value = f'**Joining**\n'
            elif self.phase != Phase.END and self.state.statuses[player.player_index] is False:
                value = f'*Folded*\n'
            else:
                value = ''
            value += f'Stack: {stack:,}'
            embed.add_field(
                name=str(player.member),
                value=value,
                inline=True
            )
        return embed

    def get_table_embed(self):
        embed = discord.Embed(
            title=f'{self.buy_in:,} {self.server.points_name.capitalize()} Texas Hold \'Em',
            colour=Colour.poker_table(),
            description=f'Buy In: {self.buy_in:,}\nBig Blind: {self.big_blind:,}\nSmall Blind: {self.small_blind:,}'
        )
        if self.state is not None and list(self.state.pots):
            pots = list(self.state.pots)
            main = pots[0]
            embed.add_field(name='Main Pot', value=f'Amount: **{main.amount:,}**')
            for pot in pots[1:]:
                pot_contributors = list(self._current_players[x] for x in pot.player_indices)
                names = and_join(list(str(x.member) for x in pot_contributors))
                embed.add_field(name='Side Pot', value=f'Contributors: {names}\nAmount: **{pot.amount:,}**')
        embed.set_image(url='attachment://river.png')
        return embed

    def get_playing_embed(self, timer: Optional[datetime] = None):
        if self.state is None:
            return discord.Embed(
                title='Waiting for next game',
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
        if current is None:
            return discord.Embed(
                title='No ones turn',
                colour=Colour.poker_playing()
            )

        embed = discord.Embed(
            title=f'Current Turn: {current.member}',
            colour=Colour.poker_playing()
        )
        embed.set_thumbnail(url=current.member.member.display_avatar.url)
        if self.phase == Phase.BETTING:
            current_bet = self.state.bets[self.waiting_for_index()]
            # min_bet = self.state.min_completion_betting_or_raising_to_amount
            # max_bet = self.state.max_completion_betting_or_raising_to_amount
            call_amt = self.state.checking_or_calling_amount
            embed.description = f'Currently Bet: {current_bet:,}\nCall Amount: {call_amt:,}'
        elif self.phase == Phase.SHOWDOWN:
            embed.description = 'Show or Muck?'
        if timer is not None:
            embed.add_field(name='Time Remaining', value=discord.utils.format_dt(timer, 'R'))
        if self._last_action:
            embed.add_field(name='Last Action', value=self._last_action)
        return embed

    def get_embeds(self, timer: Optional[datetime] = None):
        table_embed = self.get_table_embed()
        playing_embed = self.get_playing_embed(timer=timer)

        return [table_embed, playing_embed]


class TableView(discord.ui.View):
    def __init__(self, game: TexasHoldEm, *, timeout=None):
        self.game = game
        super().__init__(timeout=timeout)

        self.update_buttons()

    def update_buttons(self):
        self.join_button.label = f'Join {self.game.buy_in:,}'
        self.join_button.disabled = len(self.game.players) >= self.game.MAX_PLAYERS
        self.leave_button.disabled = len(self.game.players) == 0

    @discord.ui.button(label='Join', style=discord.ButtonStyle.green, row=4)
    async def join_button(self, interaction: discord.Interaction, _):
        member = self.game.server.members.get(interaction.user.id)
        if member in self.game.players:
            return await interaction.response.send_message('You are already in the game!', ephemeral=True)
        try:
            await self.game.add_player(member)
            await interaction.response.send_message('You have joined the game!', ephemeral=True)
            self.update_buttons()
            await self.game.update_control_message(view=self)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)

    @discord.ui.button(label='Leave', style=discord.ButtonStyle.red, row=4)
    async def leave_button(self, interaction: discord.Interaction, _):
        member = self.game.server.members.get(interaction.user.id)
        if member not in self.game.players:
            return await interaction.response.send_message('You are not in the game!', ephemeral=True)
        if self.game.waiting_for() == self.game.players[member]:
            return await interaction.response.send_message('You can not leave during your turn!', ephemeral=True)
        await self.game.withdraw(member)
        await interaction.response.send_message('You have left the game!', ephemeral=True)
        self.update_buttons()
        await self.game.update_control_message(view=self)


class BettingView(discord.ui.View):
    def __init__(self, game: TexasHoldEm, *, timeout=30):
        self.game = game
        self.state = game.state
        super().__init__(timeout=timeout)
        self.update_buttons()

    def update_buttons(self):
        if self.state.min_completion_betting_or_raising_to_amount is not None:
            self.low_bet.label = self.state.min_completion_betting_or_raising_to_amount
            self.double_bet.label = self.state.min_completion_betting_or_raising_to_amount * 2
            self.double_bet.disabled = (self.state.min_completion_betting_or_raising_to_amount * 2
                                        > self.state.max_completion_betting_or_raising_to_amount)
        else:
            self.low_bet.disabled = True
            self.double_bet.disabled = True
        if self.state.max_completion_betting_or_raising_to_amount is not None:
            self.max_bet.label = self.state.max_completion_betting_or_raising_to_amount
        else:
            self.max_bet.disabled = True
            self.custom_bet.disabled = True
        self.fold_button.disabled = not self.state.can_fold()
        self.check_button.label = 'Check' if self.state.checking_or_calling_amount == 0 \
            else f'Call {self.state.checking_or_calling_amount:,}'

    @discord.ui.button(label='low', style=discord.ButtonStyle.gray)
    async def low_bet(self, interaction: discord.Interaction, _):
        if interaction.user != self.game.waiting_for().member.member:
            return await interaction.response.send_message('It is not your turn!', ephemeral=True)
        amt = self.state.min_completion_betting_or_raising_to_amount
        self.game.process_action(self.state.complete_bet_or_raise_to(amt))
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label='double', style=discord.ButtonStyle.gray)
    async def double_bet(self, interaction: discord.Interaction, _):
        if interaction.user != self.game.waiting_for().member.member:
            return await interaction.response.send_message('It is not your turn!', ephemeral=True)
        amt = self.state.min_completion_betting_or_raising_to_amount * 2
        self.game.process_action(self.state.complete_bet_or_raise_to(amt))
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label='max', style=discord.ButtonStyle.gray)
    async def max_bet(self, interaction: discord.Interaction, _):
        if interaction.user != self.game.waiting_for().member.member:
            return await interaction.response.send_message('It is not your turn!', ephemeral=True)
        amt = self.state.max_completion_betting_or_raising_to_amount
        self.game.process_action(self.state.complete_bet_or_raise_to(amt))
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label='Custom', style=discord.ButtonStyle.gray)
    async def custom_bet(self, interaction: discord.Interaction, _):
        if interaction.user != self.game.waiting_for().member.member:
            return await interaction.response.send_message('It is not your turn!', ephemeral=True)
        modal = AmountModal(default=str(self.state.min_completion_betting_or_raising_to_amount), timeout=15)
        await interaction.response.send_modal(modal)
        await modal.wait()
        if (modal.amount_selected is not None
                and self.state.min_completion_betting_or_raising_to_amount
                <= modal.amount_selected
                <= self.state.max_completion_betting_or_raising_to_amount):
            self.game.process_action(self.state.complete_bet_or_raise_to(modal.amount_selected))
            self.stop()

    @discord.ui.button(label='Check/Call', style=discord.ButtonStyle.green, row=1)
    async def check_button(self, interaction: discord.Interaction, _):
        if interaction.user != self.game.waiting_for().member.member:
            return await interaction.response.send_message('It is not your turn!', ephemeral=True)
        await interaction.response.defer()
        self.game.process_action(self.state.check_or_call())
        self.stop()

    @discord.ui.button(label='Fold', style=discord.ButtonStyle.red, row=1)
    async def fold_button(self, interaction: discord.Interaction, _):
        if interaction.user != self.game.waiting_for().member.member:
            return await interaction.response.send_message('It is not your turn!', ephemeral=True)
        self.game.process_action(self.state.fold())
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label='Show Cards', style=discord.ButtonStyle.gray, row=4)
    async def show_cards(self, interaction: discord.Interaction, _):
        if self.game.phase == Phase.END:
            return await interaction.response.send_message('No game running!', ephemeral=True)
        member = self.game.server.members.get(interaction.user.id)
        if member not in self.game.players:
            return await interaction.response.send_message('You are not in the game!', ephemeral=True)
        player = self.game.players[member]
        embed = discord.Embed(
            title=f'{member}\'s Cards',
            colour=Colour.poker_table()
        )
        cards = tuple(self.game.state.get_down_cards(self.game._current_players.index(player)))
        img = discord.File(get_card_images(cards, 5), 'hand.png', description=str(cards))
        embed.set_image(url='attachment://hand.png')
        await interaction.response.send_message(embed=embed, file=img, ephemeral=True)
        img.close()


