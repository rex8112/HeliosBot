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
from pokerkit import *

state = NoLimitTexasHoldem.create_state(
    # Automations
    (),
    False,  # Uniform antes?
    0,  # Antes
    (2, 3),  # Blinds or straddles
    10,  # Min-bet
    (1000, 1000, 1000),  # Starting stacks
    3,  # Number of players
)

names = []
for i in range(3):
    name = input(f'Player {i} name: ')
    names.append(name)

print('Preparing Game...')
print(state.blinds_or_straddles)

while state.status:
    print('Bets', state.bets)
    if state.can_post_ante():
        print('Ante', state.post_ante())
    elif state.can_collect_bets():
        print('Collecting', state.collect_bets())
    elif state.can_post_blind_or_straddle():
        print('Post Blinds', state.post_blind_or_straddle())
    elif state.can_burn_card():
        print('Burn Cards', state.burn_card())
    elif state.can_deal_hole():
        print('Deal Hole', state.deal_hole())
    elif state.can_deal_board():
        print('Deal Board', state.deal_board())
    elif state.can_kill_hand():
        print('Kill Hand', state.kill_hand())
    elif state.can_push_chips():
        push = state.push_chips()
        print('Push Chips', push)
    elif state.can_pull_chips():
        print('Pull Chips', state.pull_chips())
    elif state.can_show_or_muck_hole_cards():
        res = state.show_or_muck_hole_cards(True)
        print('Show or Muck', res)
    else:
        if state.actor_index is not None:
            print(names[state.actor_index], list(state.get_down_cards(state.actor_index)), state.board_cards, state.stacks[state.actor_index])
        else:
            print(names[state.showdown_index], list(state.get_down_cards(state.showdown_index)), state.board_cards, state.stacks[state.showdown_index])
        print(state.total_pot_amount)
        print(state.min_completion_betting_or_raising_to_amount, state.max_completion_betting_or_raising_to_amount)
        print(state.checking_or_calling_amount)
        print('Fold: ', state.can_fold(), 'Check/Call: ', state.can_check_or_call())
        string = input('Action: ')
        print(parse_action(state, f'p{(state.actor_index if state.actor_index is not None else state.showdown_index)+1} ' + string))
