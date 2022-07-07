import json
from typing import Union, TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop


class HTTPClient:
    def __init__(self, base_url, *, loop: 'AbstractEventLoop', api_username: str, api_password: str):
        self._session = aiohttp.ClientSession(
            base_url=base_url,
            auth=aiohttp.BasicAuth(api_username, api_password)
        )

    async def request(self, url_end: str, method='GET', **params):
        url = f'/api/{url_end}'
        resp = await self._session.request(method, url, **params)
        j = await resp.json()
        return j

    async def get_server(self, guild_id: str):
        resp = await self.request(f'servers/{guild_id}/')
        return resp

    async def add_server(self, guild_id: str, **data):
        raise NotImplemented

    async def get_channel(self, channel_id: str = None, **params) -> Union[dict, list]:
        resp = None
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
