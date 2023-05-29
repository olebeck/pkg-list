from game_list import get_vita_games
from updates import GetGameUpdates, Update
import aiohttp, asyncio

from utils import limited_as_completed
from pkg import read_pkg, PkgItem
import db


client: aiohttp.ClientSession = None

async def get_pkg_filelist(info: dict) -> tuple[list[PkgItem], str]:
    url: str = info['PKG direct link']
    titleid: str = info["Title ID"]
    if not url.startswith("http"):
        return None, titleid

    r = await client.get(url)
    pkg_object = await read_pkg(r.content)
    r.close()
    if pkg_object == None:
        return None, titleid
    print("get_pkg_filelist", titleid)
    return pkg_object, titleid

async def get_updates(info):
    url: str = info['PKG direct link']
    titleid: str = info["Title ID"]  
    if not url.startswith("http"):
        return titleid, None

    updates = await GetGameUpdates(titleid, client)
    return titleid, updates

async def get_update_diffs(info: dict, updates: dict[str, Update]):
    titleid: str = info["Title ID"]

    for up in sorted(updates.values(), key=lambda k: k.ver):
        print("fetching update", titleid, up.ver)
        try:
            r = await client.get(up.url)
            pkg_object = await read_pkg(r.content)
            r.close()
            print("get_update_diffs", titleid)
        except Exception as e:
            print(e)
            return None, None
        if pkg_object == None:
            return None, None
        db.SqlAddFiles(pkg_object, titleid, up.ver)
        db.SqlAddDoneUpdate(titleid, up.ver)
    




async def main():
    global client
    client = aiohttp.ClientSession()
    tsv = await get_vita_games(client)
    
    # filter games that havent been downloaded yet
    titles = list(db.SqlGetNotDoneTitles(tsv))

    # get the game file list for every game
    tasks = (get_pkg_filelist(tsv[k]) for k in titles)
    for task in limited_as_completed(tasks, 60):
        data, titleid = await task
        if data == None:
            continue
        db.SqlAddFiles(data, titleid)
        db.SqlAddDone(titleid)

    # get a list of updates
    all_game_updates = {}
    tasks = (get_updates(tsv[k]) for k in tsv)
    for task in limited_as_completed(tasks, 60):
        titleid, updates = await task
        if updates == None:
            continue
        all_game_updates[titleid] = updates

    # get all new files
    updates = db.SqlGetNotDoneUpdates(all_game_updates)
    tasks = (get_update_diffs(tsv[titleid], updates) for titleid, updates in updates.items())
    for task in limited_as_completed(tasks, 60):
        await task

    await client.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())