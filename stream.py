import asyncio, io
from typing import IO

class ResponseStream(IO):
    def __init__(self, resp: asyncio.StreamReader):
        self._bytes = io.BytesIO()
        self._resp = resp

    async def _load_all(self):
        raise Exception("Unimplemented")
        self._bytes.seek(0, io.SEEK_END)
        async for chunk in self._iterator:
            self._bytes.write(chunk)

    async def _load_until(self, goal_position):
        current_position = self._bytes.seek(0, io.SEEK_END)
        to_load = goal_position-current_position
        if to_load <= 0:
            return
        data = await self._resp.read(to_load)
        self._bytes.write(data)

    def tell(self):
        return self._bytes.tell()

    async def read(self, size=None):
        left_off_at = self._bytes.tell()
        if size is None:
            await self._load_all()
        else:
            goal_position = left_off_at + size
            await self._load_until(goal_position)

        self._bytes.seek(left_off_at)
        return self._bytes.read(size)

    async def seek(self, position, whence=io.SEEK_SET):
        if whence == io.SEEK_END:
            await self._load_all()
        else:
            self._bytes.seek(position, whence)

async def read_uint32(stream: asyncio.StreamReader):
    return int.from_bytes(await stream.read(4), "big")

async def read_uint64(stream: asyncio.StreamReader):
    return int.from_bytes(await stream.read(8), "big")
