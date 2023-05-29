from typing import Tuple
import aiohttp
import asyncio
from game_list import get_vita_games_pending, get_ps3_games_pending
from itertools import islice
import pkg, json


def limited_as_completed(coros, limit):
    futures = [
        asyncio.ensure_future(c)
        for c in islice(coros, 0, limit)
    ]

    async def first_to_finish():
        while True:
            await asyncio.sleep(0)
            for f in futures:
                if f.done():
                    futures.remove(f)
                    try:
                        newf = next(coros)
                        futures.append(
                            asyncio.ensure_future(newf))
                    except StopIteration:
                        pass
                    return f.result()
    while len(futures) > 0:
        yield first_to_finish()


async def test_pkg(data, client: aiohttp.ClientSession) -> Tuple[Exception, str]:
    url,zrif,titleid = data['PKG direct link'], data["Title ID"]
    if not url.startswith("http"):
        return Exception(""), None, titleid, None
    print(titleid)

    try:
        pkg.zrif_decode(zrif)
    except Exception as e:
        return e, "zrif invalid", titleid, None

    r = await client.get(url)
    pkg_object = await pkg.read_pkg(r.content)
    if pkg_object == None:
        raise Exception("")
    return None, "valid", titleid, pkg_object

out = {}
valid = {}
async def main():
    client = aiohttp.ClientSession()

    tsv = await get_vita_games_pending(client)
    tsv.extend(await get_ps3_games_pending(client))
    tsv.reverse()
    tasks = (test_pkg(k, client) for k in tsv)
    for task in limited_as_completed(tasks, 60):
        err, reason, titleid, pkg_object = await task
        if err != None:
            if reason == None:
                continue
            out[titleid] = reason
        else:
            valid[titleid] = len(pkg_object.items)

    print(json.dumps(out))
    print(json.dumps(valid))

loop = asyncio.get_event_loop()
loop.run_until_complete(main())