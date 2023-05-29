import enum
from typing import List
import aiohttp
import io
import binascii
import zlib
import asyncio
import struct
from Crypto.Cipher import AES
from Crypto.Util import Counter

from stream import ResponseStream, read_uint32, read_uint64


# decode a zrif
zrif_dict = list(zlib.decompress(binascii.a2b_base64(b"eNpjYBgFo2AU0AsYAIElGt8MRJiDCAsw3xhEmIAIU4N4AwNdRxcXZ3+/EJCAkW6Ac7C7ARwYgviuQAaIdoPSzlDaBUo7QmknIM3ACIZM78+u7kx3VWYEAGJ9HV0=")))
def zrif_decode(data: str):
    d = zlib.decompressobj(wbits=10, zdict=bytes(zrif_dict))
    raw = binascii.a2b_base64(data)
    out = d.decompress(raw)
    out += d.flush()
    return out


# read from async stream at block with ctr
async def read_decrypt(stream: asyncio.StreamReader, aes_key: bytes, iv: bytes, length: int, block: int) -> bytes:
    iv_int = int.from_bytes(iv, "big")+block
    ctr = Counter.new(128, initial_value=iv_int)
    key = AES.new(aes_key, mode=AES.MODE_CTR, counter=ctr)
    return key.decrypt(await stream.read(length))




pkg_ps3_key = bytes([ 0x2e, 0x7b, 0x71, 0xd7, 0xc9, 0xc9, 0xa1, 0x4e, 0xa3, 0x22, 0x1f, 0x18, 0x88, 0x28, 0xb8, 0xf8 ])
pkg_psp_key = bytes([ 0x07, 0xf2, 0xc6, 0x82, 0x90, 0xb5, 0x0d, 0x2c, 0x33, 0x81, 0x8d, 0x70, 0x9b, 0x60, 0xe6, 0x2b ])
pkg_vita_2  = bytes([ 0xe3, 0x1a, 0x70, 0xc9, 0xce, 0x1d, 0xd7, 0x2b, 0xf3, 0xc0, 0x62, 0x29, 0x63, 0xf2, 0xec, 0xcb ])
pkg_vita_3  = bytes([ 0x42, 0x3a, 0xca, 0x3a, 0x2b, 0xd5, 0x64, 0x9f, 0x96, 0x86, 0xab, 0xad, 0x6f, 0xd8, 0x80, 0x1f ])
pkg_vita_4  = bytes([ 0xaf, 0x07, 0xfd, 0x59, 0x65, 0x25, 0x27, 0xba, 0xf1, 0x33, 0x89, 0x66, 0x8b, 0x17, 0xd9, 0xea ])

class pkg_type(enum.IntEnum):
    PKG_TYPE_VITA_APP = 0
    PKG_TYPE_VITA_DLC = 1
    PKG_TYPE_VITA_PATCH = 2
    PKG_TYPE_VITA_PSM = 3
    PKG_TYPE_PSP = 4
    PKG_TYPE_PSX = 5

class PkgItemFlags(enum.IntFlag):
    folder = 4

class PkgItem:
    name: str
    flags: int
    size:  int
    info_offset: int

    def __repr__(self):
        return f"PkgItem('{self.name}')"

class Pkg:
    revision:     bytes
    pkgtype:      bytes
    meta_offset:  int
    meta_count:   int
    meta_size:    int
    item_count:   int
    item_offset:  int
    item_size:    int
    total_size:   int
    enc_offset:   int
    enc_size:     int
    content_id:   str
    digest:       bytes
    iv:           bytes
    key_type:     int
    content_type: int
    sfo_offset:   int
    sfo_size:     int

    items: List[PkgItem]
    def __init__(self) -> None:
        self.items = list()

    @staticmethod
    async def from_stream(r: asyncio.StreamReader) -> "Pkg":
        stream = ResponseStream(r)
        pkg = Pkg()
        if await stream.read(4) != b'\x7fPKG':
            raise Exception("wrong magic")
        pkg.revision    = await stream.read(2)
        pkg.pkgtype     = await stream.read(2)
        pkg.meta_offset = await read_uint32(stream)
        pkg.meta_count  = await read_uint32(stream)
        pkg.meta_size   = await read_uint32(stream)
        pkg.item_count  = await read_uint32(stream)
        pkg.total_size  = await read_uint64(stream)
        pkg.enc_offset  = await read_uint64(stream)
        assert pkg.enc_offset % 16 == 0
        pkg.enc_size    = await read_uint64(stream)
        pkg.content_id  = (await stream.read(0x24)).decode("ascii")
        _               = await stream.read(0x0c) # padding
        pkg.digest      = await stream.read(0x10)
        pkg.iv          = await stream.read(0x10)
        await stream.seek(0xe7, io.SEEK_SET)
        pkg.key_type    = int.from_bytes(await stream.read(1), "big") & 7

        pkg.content_type = 0
        pkg.item_offset = 0
        pkg.item_size = 0
        pkg.sfo_offset = 0
        pkg.sfo_size = 0
        for _ in range(pkg.meta_count):
            await stream.seek(pkg.meta_offset, 0)
            meta_elem_type = await read_uint32(stream)
            meta_elem_size = await read_uint32(stream)
            if meta_elem_type == 2:
                pkg.content_type = content_type = await read_uint32(stream)
            elif meta_elem_type == 13:
                pkg.item_offset = await read_uint32(stream)
                pkg.item_size   = await read_uint32(stream)
            elif meta_elem_type == 14:
                pkg.sfo_offset = await read_uint32(stream)
                pkg.sfo_size   = await read_uint32(stream)
            pkg.meta_offset += 2 * 4 + meta_elem_size

        PkgType = 0
        if content_type == 6:
            PkgType = pkg_type.PKG_TYPE_PSX
        elif content_type == 7 or content_type == 0xe or content_type == 0xf or content_type == 0x10:
            PkgType = pkg_type.PKG_TYPE_PSP
        elif content_type == 0x15:
            PkgType = pkg_type.PKG_TYPE_VITA_APP
        elif content_type == 0x16:
            PkgType = pkg_type.PKG_TYPE_VITA_DLC
        elif content_type == 0x18:
            PkgType = pkg_type.PKG_TYPE_VITA_PSM
        else:
            raise Exception(f"unsupported content_type {content_type}")

        if PkgType == pkg_type.PKG_TYPE_PSP:
            raise NotImplementedError("psp")
        if PkgType == pkg_type.PKG_TYPE_VITA_PSM:
            raise NotImplementedError("psm")
        if PkgType == pkg_type.PKG_TYPE_PSX:
            print("this is psx...")
            return None

        main_key = bytes()
        if pkg.key_type == 1:
            main_key = pkg_psp_key
            ps3_key = AES.new(pkg_ps3_key, AES.MODE_ECB)
        elif pkg.key_type == 2:
            key1 = AES.new(pkg_vita_2, AES.MODE_ECB)
            main_key = key1.encrypt(pkg.iv)
        elif pkg.key_type == 3:
            key1 = AES.new(pkg_vita_3, AES.MODE_ECB)
            main_key = key1.encrypt(pkg.iv)
        elif pkg.key_type == 4:
            key1 = AES.new(pkg_vita_4, AES.MODE_ECB)
            main_key = key1.encrypt(pkg.iv)

        for item_index in range(pkg.item_count):
            item = PkgItem()
            item.info_offset = pkg.item_offset + item_index * 32
            assert item.info_offset % 16 == 0

            await stream.seek(pkg.enc_offset + item.info_offset, io.SEEK_SET)
            item_info = await read_decrypt(stream, main_key, pkg.iv, 32, item.info_offset // 16)
            (name_offset, name_size, data_offset, item.size) = struct.unpack(">IIII", item_info[0:16])
            psp_type = item_info[24]
            item.flags = PkgItemFlags(item_info[27])

            assert name_offset % 16 == 0
            await stream.seek(pkg.enc_offset + name_offset, io.SEEK_SET)
            name_b = await read_decrypt(stream, main_key, pkg.iv, name_size, name_offset // 16)
            item.name = name_b.decode("utf-8")

            #assert data_offset % 16 == 0

            pkg.items.append(item)
        stream.close()
        return pkg


# test
if __name__ == "__main__":
    URL = "http://ares.dl.playstation.net/psm-runtime/IP9100-PCSI00011_00-PSMRUNTIME000000.pkg"
    ZRIF = "KO5ifR1dg/J5YXzPAEtDiGpPkPGGIPsDgn2DQv1CPH1dIZbi89+nS4wpR/vWpWUGfu9bZv26YzTGBzcAACA6FcUA"

    async def main():
        client = aiohttp.ClientSession()
        r = await client.get(URL)
        pkg_object = await Pkg.from_stream(r.content)
        for item in pkg_object.items:
            print(item.name)
        r.close()
        print()
        await client.close()

    asyncio.get_event_loop().run_until_complete(main())
