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

from typing import Union, TYPE_CHECKING

import aiohttp

from .exceptions import HTTPError

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop


class HTTPClient:
    def __init__(self, base_url, *, loop: 'AbstractEventLoop', api_username: str, api_password: str, name_api_key: str):
        self._session = aiohttp.ClientSession(
            base_url=base_url,
            auth=aiohttp.BasicAuth(api_username, api_password)
        )
        name_headers = {'X-Api-Key': name_api_key}
        self._name_session = aiohttp.ClientSession(
            headers=name_headers
        )

    @staticmethod
    async def json_or_none(cr: aiohttp.ClientResponse):
        if cr.status == 404:
            return None
        else:
            return await cr.json(content_type=cr.headers.get('Content-Type'))

    async def request(self, url_end: str, method='GET', **params):
        url = f'/api/{url_end}'
        resp = await self._session.request(method, url, **params)
        if resp.status not in [200, 201, 204, 404]:
            raise HTTPError(resp.status, await resp.text())
        j = await self.json_or_none(resp)
        return j

    async def request_names(self, quantity: int, *, name_type='firstname') -> list[str]:
        url = 'https://randommer.io/api/Name'
        resp = await self._name_session.get(url, params={'nameType': name_type, 'quantity': quantity})
        if resp.status == 200:
            return await resp.json()

    async def get_server(self, guild_id: int = None):
        if guild_id:
            resp = await self.request(f'servers/{guild_id}/')
        else:
            resp = await self.request(f'servers/')
        return resp

    async def post_server(self, json_data: Union[dict, list]):
        resp = await self.request(f'servers/', method='POST', json=json_data)
        return resp

    async def patch_server(self, json_data: Union[dict, list]):
        resp = await self.request(f'servers/{json_data.get("id")}/', method='PATCH', json=json_data)
        return resp

    async def get_channel(self, channel_id: int = None, **params) -> Union[dict, list]:
        if channel_id:
            resp = await self.request(f'channels/{channel_id}/')
        else:
            resp = await self.request(f'channels/', params=params)
        return resp

    async def post_channel(self, json_data: Union[dict, list]):
        resp = await self.request('channels/', method='POST', json=json_data)
        return resp

    async def patch_channel(self, json_data: Union[dict, list]):
        resp = await self.request(f'channels/{json_data.get("id")}/', method='PATCH', json=json_data)
        return resp

    async def del_channel(self, id: int):
        resp = await self.request(f'channels/{id}/', method='DELETE')
        return resp

    async def get_member(self, id: int = None, **params) -> Union[dict, list]:
        if id:
            resp = await self.request(f'members/{id}/')
        else:
            resp = await self.request(f'members/', params=params)
        return resp

    async def post_member(self, json_data: Union[dict, list]):
        resp = await self.request('members/', method='POST', json=json_data)
        return resp

    async def patch_member(self, json_data: Union[dict, list]):
        resp = await self.request(f'members/{json_data.get("id")}/', method='PATCH', json=json_data)
        return resp

    async def del_member(self, mem_id: int):
        resp = await self.request(f'members/{mem_id}/', method='DELETE')
        return resp

    async def get_stadium(self, *, stadium_id: int = None, **params):
        if stadium_id:
            resp = await self.request(f'stadium/{stadium_id}')
        else:
            resp = await self.request(f'stadium/', params=params)
        return resp

    async def post_stadium(self, json_data: Union[dict, list]):
        resp = await self.request('stadium/', method='POST', json=json_data)
        return resp

    async def patch_stadium(self, json_data: Union[dict, list]):
        resp = await self.request(f'stadium/{json_data.get("server")}/', method='PATCH', json=json_data)
        return resp

    async def del_stadium(self, stadium_id: int):
        resp = await self.request(f'stadium/{stadium_id}/', method='DELETE')
        return resp

    async def get_horse(self, *, horse_id: int = None, **params):
        if horse_id:
            resp = await self.request(f'horses/{horse_id}')
        else:
            resp = await self.request(f'horses/', params=params)
        return resp

    async def post_horse(self, json_data: Union[dict, list]):
        resp = await self.request('horses/', method='POST', json=json_data)
        return resp

    async def patch_horse(self, json_data: Union[dict, list]):
        resp = await self.request(f'horses/{json_data.get("id")}/', method='PATCH', json=json_data)
        return resp

    async def del_horse(self, horse_id: int):
        resp = await self.request(f'horses/{horse_id}/', method='DELETE')
        return resp

    async def get_race(self, *, race_id: int = None, **params):
        if race_id:
            resp = await self.request(f'races/{race_id}')
        else:
            resp = await self.request(f'races/', params=params)
        return resp

    async def post_race(self, json_data: Union[dict, list]):
        resp = await self.request('races/', method='POST', json=json_data)
        return resp

    async def patch_race(self, json_data: Union[dict, list]):
        resp = await self.request(f'races/{json_data.get("id")}/', method='PATCH', json=json_data)
        return resp

    async def del_race(self, race_id: int):
        resp = await self.request(f'races/{race_id}/', method='DELETE')
        return resp

    async def get_record(self, *, record_id: int = None, **params):
        if record_id:
            resp = await self.request(f'records/{record_id}/')
        else:
            resp = await self.request(f'records/', params=params)
        return resp

    async def post_record(self, json_data: Union[dict, list]):
        resp = await self.request(f'records/', method='POST', json=json_data)
        return resp

    async def patch_record(self, json_data: Union[dict, list]):
        resp = await self.request(f'records/{json_data["id"]}/',
                                  method='PATCH', json=json_data)
        return resp

    async def del_record(self, record_id: int):
        resp = await self.request(f'records/{record_id}/', method='DELETE')
        return resp

    async def get_auction(self, *, auction_id: int = None, **params):
        if auction_id:
            resp = await self.request(f'auctions/{auction_id}/')
        else:
            resp = await self.request(f'auctions/', params=params)
        return resp

    async def post_auction(self, json_data: Union[dict, list]):
        resp = await self.request(f'auctions/', method='POST', json=json_data)
        return resp

    async def patch_auction(self, json_data: Union[dict, list]):
        resp = await self.request(f'auctions/{json_data["id"]}/',
                                  method='PATCH', json=json_data)
        return resp

    async def del_auction(self, auction_id: int):
        resp = await self.request(f'auctions/{auction_id}/', method='DELETE')
        return resp

    async def post_template(self, json_data: Union[dict, list]):
        resp = await self.request('templates/', method='POST', json=json_data)
        return resp

    async def patch_template(self, json_data: Union[dict, list]):
        resp = await self.request(f'templates/{json_data.get("id")}/', method='PATCH', json=json_data)
        return resp

    async def del_template(self, tem_id: int):
        resp = await self.request(f'templates/{tem_id}/', method='DELETE')
        return resp
