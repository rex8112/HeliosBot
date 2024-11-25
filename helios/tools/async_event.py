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
from typing import Callable, Awaitable, Any


class AsyncEvent:
    def __init__(self):
        self._listeners: list[Callable[[Any], Awaitable]] = []

    async def __call__(self, *args, **kwargs):
        tasks = [listener(*args, **kwargs) for listener in self._listeners]
        await asyncio.gather(*tasks)

    @property
    def on(self):
        def wrapper(func: Callable[[Any], Awaitable]):
            self.listen(func)
            return func
        return wrapper

    def listen(self, listener):
        if listener in self._listeners:
            return
        self._listeners.append(listener)

    def unlisten(self, listener):
        if listener not in self._listeners:
            return
        self._listeners.remove(listener)