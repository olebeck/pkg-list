import asyncio
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import List
import aiohttp

import hashlib
import hmac

# key for the update urls
key = bytes([0xE5, 0xE2, 0x78, 0xAA, 0x1E, 0xE3, 0x40, 0x82, 0xA0, 0x88, 0x27, 0x9C, 0x83, 0xF9, 0xBB, 0xC8,
	   0x06, 0x82, 0x1C, 0x52, 0xF2, 0xAB, 0x5D, 0x2B, 0x4A, 0xBD, 0x99, 0x54, 0x50, 0x35, 0x51, 0x14])

# get update url for an title
def xml_link(titleid: str):
    titleid = titleid.upper()
    np_env = "np"

    h = hmac.new(key, (np_env + "_" + titleid).encode("ascii"), hashlib.sha256)
    out = h.hexdigest()
    return f"http://gs-sec.ww.{np_env}.dl.playstation.net/pl/{np_env}/{titleid}/{out}/{titleid}-ver.xml"


class Update:
    ver: str
    url: str

    def __init__(self, ver: str, url: str):
        self.ver = ver
        self.url = url


async def GetGameUpdates(titleid: str, client: aiohttp.ClientSession) -> List[Update]:
    r = await client.get(xml_link(titleid))
    if r.status == 404:
        return {}
    if r.status != 200:
        raise Exception(r.status)
    content = await r.read()
    if len(content) == 0:
        return {}
    root = ET.parse(BytesIO(content))
    updates = root.findall(".//package")
    out = {}
    for u in updates:
        item = Update(u.attrib["version"], u.attrib["url"])
        out[item.ver] = item
    return out


# test
async def main():
    client = aiohttp.ClientSession()
    updates = await GetGameUpdates("PCSE00491", client)
    print() # break here in debugger

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())