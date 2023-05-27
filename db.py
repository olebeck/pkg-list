from updates import Update
from pkg import Pkg
import mysql.connector
import hashlib


class sql_conf(object):
    user = "user"
    password = "pass"
    host = "127.0.0.1"
    database = "vita_files"


db = None

def getSQL():
    global db
    if db == None:
        db = mysql.connector.connect(
            host     = sql_conf.host,
            user     = sql_conf.user,
            password = sql_conf.password,
            database = sql_conf.database
        )
    return db


def SqlGetNotDoneTitles(list_titles: dict[dict]) -> list[str]:
    db = getSQL()
    cursor: mysql.connector.connection_cext.CMySQLCursor = db.cursor()
    sql = "SELECT titleid FROM indexed_games"
    cursor.execute(sql)
    res = [r[0] for r in cursor.fetchall()]
    return filter(lambda k: k not in res, list_titles.keys())


def SqlGetNotDoneUpdates(list_title_updates: dict[str, dict[str, Update]]) -> dict[str, list[Update]]:
    db = getSQL()
    cursor: mysql.connector.connection_cext.CMySQLCursor = db.cursor()
    cursor.execute("SELECT titleid, version FROM indexed_updates")
    done_updates = cursor.fetchall()
    for (titleid, version) in done_updates:
        if list_title_updates.get(titleid, {}).get(version):
            list_title_updates[titleid].pop(version)
    cursor.close()

    keys = list(list_title_updates.keys())
    for k in keys:
        if len(list_title_updates[k]) == 0:
            list_title_updates.pop(k)
    return list_title_updates


def SqlAddFiles(data: Pkg, titleid: str, version: str = "1"):
    db = getSQL()
    cursor: mysql.connector.connection_cext.CMySQLCursor = db.cursor()
    values = ', '.join([f'("{titleid}", "{item.name}", {item.size}, {item.flags}, {version}, "{hashlib.sha1((titleid + item.name).encode("utf8")).hexdigest()}")' for item in data.items])
    cursor.execute(f"INSERT IGNORE INTO gamedata (titleid, filename, size, flags, version, titleid_filename_hash) VALUES {values}")
    db.commit()
    cursor.close()


def SqlAddDone(titleid: str):
    db = getSQL()
    cursor: mysql.connector.connection_cext.CMySQLCursor = db.cursor()
    sql = "INSERT INTO indexed_games (titleid) VALUES (%s)"
    cursor.execute(sql,(titleid,))
    db.commit()
    cursor.close()

def SqlAddDoneUpdate(titleid: str, ver: str):
    db = getSQL()
    cursor: mysql.connector.connection_cext.CMySQLCursor = db.cursor()
    sql = "INSERT INTO indexed_updates (titleid, version) VALUES (%s, %s)"
    cursor.execute(sql,(titleid, ver))
    db.commit()
    cursor.close()
