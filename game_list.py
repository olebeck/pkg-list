def csv(text: str):
    tsv = []
    lines = text.splitlines(False)
    head = lines[0].split("\t")
    lines.pop(0)
    for line in lines:
        data = line.split("\t")
        item = {head[i]: data[i] for i in range(len(data))}
        tsv.append(item)
    return tsv

async def get_vita_games(client):
    r = await client.get("https://nopaystation.com/tsv/PSV_GAMES.tsv")
    text = (await r.read()).decode("utf8")
    return {a["Title ID"]: a for a in csv(text)}


async def get_vita_games_pending(client):
    r = await client.get("https://nopaystation.com/tsv/pending/PSV_GAMES.tsv")
    text = (await r.read()).decode("utf8")
    return csv(text)

async def get_ps3_games_pending(client):
    r = await client.get("https://nopaystation.com/tsv/pending/PS3_GAMES.tsv")
    text = (await r.read()).decode("utf8")
    return csv(text)