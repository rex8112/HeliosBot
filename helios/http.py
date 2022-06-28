import asyncio
import aiohttp


class HTTPClient:
    def __init__(self, base_url):
        self._session = aiohttp.ClientSession(base_url)

    async def request(self, url_end: str, method='GET'):
        url = f'/api/{url_end}'
        return await self._session.request(method, url)
