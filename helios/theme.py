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


class Theme:
    def __init__(self, name: str, roles: list['ThemeRole']):
        self.name = name
        self.roles = roles


class ThemeRole:
    def __init__(self, name: str, color: str, maximum: int):
        self.name = name
        self.color = color
        self.maximum = maximum

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<ThemeRole {self.name}>'

    def to_dict(self):
        return {
            'name': self.name,
            'color': self.color,
            'maximum': self.maximum
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['name'], data['color'], data['maximum'])
