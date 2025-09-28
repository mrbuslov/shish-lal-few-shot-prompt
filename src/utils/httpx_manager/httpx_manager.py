import asyncio
import time
from asyncio import Queue, QueueFull, QueueEmpty
from contextlib import suppress
from dataclasses import dataclass
from http import HTTPMethod

import httpx

from .httpx_settings import httpx_settings


@dataclass
class HTTPXClientData:
    client: httpx.AsyncClient
    request_count: int
    created_at: float


class HTTPXManager:
    def __init__(self):
        self._client_limit = httpx_settings.CLIENT_REQUEST_LIMIT
        self._client_expire_sec = httpx_settings.CLIENT_EXPIRE_SECONDS
        self._queue_size = httpx_settings.CLIENT_POOL_SIZE

        self._semaphore = asyncio.Semaphore(httpx_settings.MAX_CONCURRENT_REQUESTS)
        self._timeout = httpx_settings.TIMEOUT
        self._limits = httpx.Limits(max_connections=200, max_keepalive_connections=10)

        self._clients_queue: Queue[HTTPXClientData] = Queue(self._queue_size)

    def _create_client(self) -> HTTPXClientData:
        return HTTPXClientData(
            client=httpx.AsyncClient(
                http2=True, timeout=self._timeout, limits=self._limits
            ),
            request_count=0,
            created_at=time.time(),
        )

    async def _get_client(self) -> HTTPXClientData:
        try:
            return self._clients_queue.get_nowait()
        except QueueEmpty:
            return self._create_client()

    async def _return_client(self, client_data: HTTPXClientData):
        client_data.request_count += 1
        expired = (time.time() - client_data.created_at) > self._client_expire_sec
        limit_reached = client_data.request_count >= self._client_limit

        if expired or limit_reached:
            await client_data.client.aclose()
            with suppress(QueueFull):
                await self._clients_queue.put(self._create_client())
        else:
            with suppress(QueueFull):
                await self._clients_queue.put(client_data)

    async def async_request(
        self,
        url: str,
        method: HTTPMethod = "GET",
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        files: dict = None,
        json: dict = None,
    ):
        async with self._semaphore:
            client_data = await self._get_client()
            try:
                response = await client_data.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    files=files,
                    json=json,
                )
                return response
            finally:
                await self._return_client(client_data)


httpx_manager = HTTPXManager()
