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
from typing import TYPE_CHECKING
from enum import Enum

from pokerkit import NoLimitTexasHoldem

from .game import Game

if TYPE_CHECKING:
    from ..member import HeliosMember


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


class TexasHoldEm(Game):
    def __init__(self, players: list['HeliosMember'], *, buy_in: int):
        super().__init__(players)
        self.buy_in = buy_in
        self._stacks = [buy_in for _ in players]
        self.state = None
        self.phase: Phase = Phase.END

    def create_state(self):
        self.state = NoLimitTexasHoldem.create_state(
            (),
            False,
            0,
            (int(self.buy_in * 0.1), int(self.buy_in * 0.05)),
            int(self.buy_in * 0.01),
            self._stacks,
            len(self.players)
        )
        self.evaluate_phase()

    def evaluate_phase(self):
        if self.state is None:
            self.phase = Phase.END
