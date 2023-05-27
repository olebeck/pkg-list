import aiohttp, asyncio
import pkg

URL = "http://gs.ww.np.dl.playstation.net/ppkg/np/PCSE00491/PCSE00491_T76/8c6217596877cd52/UP4433-PCSE00491_00-MINECRAFTVIT0000-A0183-V0100-13bef2e338cee5dd159ee4308e95fd3831dfe1e9-SP-PE.pkg"
ZRIF = "KO5ifR1dQ+eHBpiYGBtDTTWxNATZ7+vp5+oc5OgWEuYJdgQ+/6UKywpYyTe7Tvj1M4ZlQzzbII8O5pGeHgG+dhKI"

async def main():
    client = aiohttp.ClientSession()
    r = await client.get(URL)
    pkg_object = await pkg.read_pkg(r.content, ZRIF)
    print()

asyncio.get_event_loop().run_until_complete(main())