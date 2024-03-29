from typing import Any, Dict, Optional

from telegram import Update


# Update相关


def __isint(a: str) -> bool:
    try:
        int(a)
    except Exception:
        return False
    return True


def getchatid(update: Update) -> int:
    """返回effective_chat.id"""
    return update.effective_chat.id


def getmsgfromid(update: Update) -> int:
    """返回message.from_user.id"""
    return update.message.from_user.id


def isprivatemsg(update: Update) -> bool:
    return update.effective_chat.type == "private"


def isgroupmsg(update: Update) -> bool:
    return update.effective_chat.type.find("group") != -1


def ischannel(update: Update) -> bool:
    return update.effective_chat.type == "channel"


def popallempties(d: Dict[Any, dict]) -> bool:
    """将二层字典中一层的空值对应的键删除。如果有空值，返回True，否则返回False"""
    ans: bool = False
    for key in d:
        if not d[key]:
            ans = True
            d.pop(key)
    return ans


def findattrindict(d: dict, key: str) -> Optional[dict]:
    """从字典（键为字符串，值为字典或`int`, `str`, `bool`类型）中找到某个键所在的那层字典并返回。
    搜索子字典时，如果`key`不是`global`，忽略`tempstatus`对应的字典。"""
    if key in d:
        return d

    for k1 in d:
        if not isinstance(d[k1], dict) or (k1 == "tempstatus" and key != "GLOBAL"):
            continue
        t = findattrindict(d[k1], key)
        if t:
            return t

    return None


def istrueconsttype(val) -> bool:
    """如果val是int, str, bool才返回True"""
    return type(val) is int or type(val) is str or type(val) is bool


def isconsttype(val) -> bool:
    if istrueconsttype(val):
        return True
    if isinstance(val, list):
        for e in val:
            if not isconsttype(e):
                return False
        return True
    if isinstance(val, dict):
        for k in val:
            v = val[k]
            if not isconsttype(v) or not isconsttype(k):
                return False
        return True
    return False


def isallkeyint(d: dict) -> bool:
    for key in d:
        if not __isint(key):
            return False
    return True


def turnkeyint(d: dict) -> Dict[int, Any]:
    dd: Dict[int, Any] = {}
    for key in d:
        dd[int(key)] = d[key]
    return dd


def tobool(x: str) -> bool:
    if x in ["F", "false", "False", "假"]:
        return False
    elif x in ["T", "true", "True", "真"]:
        return True
    raise TypeError("不是可识别的bool")


def plainNewCard() -> dict:
    t = {
        "id": -1,
        "playerid": 0,
        "groupid": 0,
        "data": {
        },
        "info": {
        },
        "skill": {
            "points": -1
        },
        "interest": {

        },
        "suggestskill": {

        },
        "attr": {
            "build": -10,
            "DB": "",
            "MOV": 0,
            "atktimes": 1,
            "sandown": "0/0",
            "armor": ""
        },
        "background": {
            "description": "",
            "faith": "",
            "vip": "",
            "viplace": "",
            "preciousthing": "",
            "speciality": "",
            "dmg": "",
            "terror": "",
            "myth": "",
            "thirdencounter": ""
        },
        "tempstatus": {
            "GLOBAL": 0
        },
        "item": [],
        "assets": "",
        "type": "PL",
        "discard": False,
        "status": "alive"
    }
    return t


def templateNewCard() -> dict:
    """NPC/怪物的卡模板"""
    t = {
        "id": -1,
        "playerid": 0,
        "groupid": 0,
        "data": {
            "STR": 0,
            "CON": 0,
            "SIZ": 0,
            "DEX": 0,
            "APP": 0,
            "INT": 0,
            "POW": 0,
            "EDU": 0,
            "LUCK": 0
        },
        "info": {
            "age": 0,
            "job": "",
            "name": "",
            "sex": ""
        },
        "skill": {
            "points": 0,
            "skills": {}
        },
        "interest": {
            "points": 0,
            "skills": {}
        },
        "suggestskill": {
            "skills": {}
        },
        "attr": {
            "SAN": 0,
            "MAXSAN": 99,
            "MAGIC": 0,
            "MAXHP": 0,
            "HP": 0,
            "build": -10,
            "DB": "",
            "MOV": 0,
            "atktimes": 1,
            "sandown": "1/1d6",
            "armor": ""
        },
        "background": {
            "description": "",
            "faith": "",
            "vip": "",
            "viplace": "",
            "preciousthing": "",
            "speciality": "",
            "dmg": "",
            "terror": "",
            "myth": "",
            "thirdencounter": ""
        },
        "tempstatus": {
            "GLOBAL": 0
        },
        "item": [],
        "assets": "",
        "type": "PL",
        "discard": False,
        "status": "alive",
        "isgamecard": False
    }
    return t
