# -*- coding:utf-8 -*-

from typing import Any, Dict


def popallempties(d: Dict[Any, dict]) -> bool:
    """将二层字典中一层的空值对应的键删除。如果有空值，返回True，否则返回False"""
    ans: bool = False
    for key in d:
        if not d[key]:
            ans = True
            d.pop(key)
    return ans


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
        # "cardcheck": {
        #     "check1": False,  # 年龄是否设定
        #     "check2": False,  # str, con, dex等设定是否完成
        #     "check3": False,  # job是否设定完成
        #     "check4": False,  # skill是否设定完成
        #     "check5": False  # 名字等是否设定完成
        # },
        "attr": {
            "build": -10,
            "DB": "-100",
            "MOV": 0,
            "atktimes": 1,
            "sandown": "0/0",
            "Armor": ""
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
        "item": "",
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
            "AGE": 0,
            "job": "",
            "name": "",
            "sex": ""
        },
        "skill": {
            "points": 0
        },
        "interest": {
            "points": 0
        },
        "suggestskill": {

        },
        # "cardcheck": {
        #     "check1": False,  # 年龄是否设定
        #     "check2": False,  # str, con, dex等设定是否完成
        #     "check3": False,  # job是否设定完成
        #     "check4": False,  # skill是否设定完成
        #     "check5": False  # 名字等是否设定完成
        # },
        "attr": {
            "SAN": 0,
            "MAXSAN": 99,
            "MAGIC": 0,
            "MAXLP": 0,
            "LP": 0,
            "build": -10,
            "DB": "-100",
            "MOV": 0,
            "atktimes": 1,
            "sandown": "1/1d6",
            "Armor": ""
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
        "item": "",
        "assets": "",
        "type": "PL",
        "discard": False,
        "status": "alive"
    }
    return t

