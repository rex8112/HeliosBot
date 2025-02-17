#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
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

import discord


class Colour:
    @staticmethod
    def helios():
        return discord.Colour.from_str('#FDB813')

    @staticmethod
    def success():
        return discord.Colour.green()

    @staticmethod
    def failure():
        return discord.Colour.red()

    @staticmethod
    def violation():
        return discord.Colour.red()

    @staticmethod
    def music():
        return Colour.helios()

    @staticmethod
    def playlist():
        return discord.Colour.from_str('#a6790d')

    @staticmethod
    def poker_table():
        return discord.Colour.from_str('#35654d')

    @staticmethod
    def poker_players():
        return Colour.helios()

    @staticmethod
    def poker_playing():
        return discord.Colour.from_str('#08adc7')

    @staticmethod
    def actions():
        return discord.Colour.from_str('#e6485d')

    @staticmethod
    def store():
        return Colour.helios()

    @staticmethod
    def error():
        return discord.Colour.red()

    @staticmethod
    def choice():
        return discord.Colour.blurple()

    @staticmethod
    def inventory():
        return Colour.helios()
