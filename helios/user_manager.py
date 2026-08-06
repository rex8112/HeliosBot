#  MIT License
#
#  Copyright (c) 2026 Riley Winkler
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
from .helios_user import HeliosUser
from .tools import utc_now


class UserManager:
    def __init__(self):
        self.users = {}
        self.last_interaction = {}

    def get(self, _id: int):
        user = self.users.get(_id)
        if user is None:
            return None
        self.last_interaction[_id] = utc_now()
        return user

    def add(self, user: HeliosUser):
        if user.id in self.users:
            raise KeyError("User already exists")
        self.users[user.id] = user
        self.last_interaction[user.id] = utc_now()

    def remove(self, _id: int):
        self.users.pop(_id)
        self.last_interaction.pop(_id)