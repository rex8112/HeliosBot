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

from discord import ui, ButtonStyle, Interaction

if TYPE_CHECKING:
    from ..dynamic_voice import DynamicVoiceChannel


class DynamicVoiceView(ui.View):
    def __init__(self, voice: 'DynamicVoiceChannel'):
        super().__init__(timeout=None)
        self.voice = voice
        self.dynamic_shop.disabled = True
        self.dynamic_game_controller.disabled = True
        self.dynamic_split.disabled = True

    def get_embed(self):
        ...

    @ui.button(label='Shop', style=ButtonStyle.blurple)
    async def dynamic_shop(self, button: ui.Button, interaction: Interaction):
        ...

    @ui.button(label='Game Controller', style=ButtonStyle.blurple)
    async def dynamic_game_controller(self, button: ui.Button, interaction: Interaction):
        ...

    @ui.button(label='Split', style=ButtonStyle.blurple)
    async def dynamic_split(self, button: ui.Button, interaction: Interaction):
        ...


class PrivateVoiceView(ui.View):
    def __init__(self, voice: 'DynamicVoiceChannel'):
        super().__init__(timeout=None)
        self.voice = voice

