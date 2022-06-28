from typing import Union

import aiohttp


class HTTPClient:
    def __init__(self, base_url, api_username, api_password):
        self._session = aiohttp.ClientSession(
            base_url=base_url,
            auth=aiohttp.BasicAuth(api_username, api_password)
        )

    async def request(self, url_end: str, method='GET', **params):
        url = f'/api/{url_end}'
        resp = await self._session.request(method, url, **params)
        return await resp.json()

    async def get_server(self, guild_id: str):
        resp = await self.request(f'/servers/{guild_id}/')
        return resp

    async def add_server(self, guild_id: str, **data):
        raise NotImplemented

    async def get_channel(self, channel_id: str = None, **params) -> Union[dict, list]:
        resp = None
        if channel_id:
            resp = await self.request(f'/channels/{channel_id}/')
        else:
            resp = await self.request(f'/channels/', **params)
        return resp
