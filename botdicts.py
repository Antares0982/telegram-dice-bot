# -*- coding:utf-8 -*-
import json
from typing import Tuple, List
from cfg import *
from gameclass import *


def writekpinfo(dict1: dict) -> None:
    with open(PATH_GROUP_KP, "w", encoding="utf-8") as f:
        json.dump(dict1, f, indent=4)


def writecards(listofdict) -> None:
    with open(PATH_CARDSLIST, "w", encoding="utf-8") as f:
        json.dump(listofdict, f, indent=4)


def writegameinfo(listofobj: List[GroupGame]) -> None:
    savelist = []
    for i in range(len(listofobj)):
        newdict = {}
        newdict["groupid"] = listofobj[i].groupid
        newdict["kpid"] = listofobj[i].kpid
        newdict["cards"] = listofobj[i].cards
        savelist.append(newdict)
    with open(PATH_ONGAME, "w", encoding="utf-8") as f:
        json.dump(savelist, f, indent=4)


def readinfo() -> Tuple[dict, list, list]:
    with open(PATH_GROUP_KP, "r", encoding="utf-8") as f:
        gpkpdict = json.load(f)
    with open(PATH_CARDSLIST, "r", encoding="utf-8") as f:
        cardslist = json.load(f)
    with open(PATH_ONGAME, "r", encoding="utf-8") as f:
        ongamelistdict = json.load(f)
    ongamelist = []
    for i in range(len(ongamelistdict)):
        ongamelistdict.append(GroupGame(
            groupid=ongamelistdict[i]["groupid"], kpid=ongamelist[i]["kpid"], cards=ongamelist[i]["cards"]))
    return gpkpdict, cardslist, ongamelist


def readskilldict() -> dict:
    with open(PATH_SKILLDICT, 'r', encoding="utf-8") as f:
        d = json.load(f)
    return d

def readjobdict() -> dict:
    with open(PATH_JOBDICT, 'r', encoding='utf-8') as f:
        d = json.load(f)
    return d