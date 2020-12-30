# -*- coding:utf-8 -*-
import json
from typing import Tuple, List
from cfg import *
from gameclass import *


def writekpinfo(dict1: dict) -> None:
    with open(PATH_GROUP_KP, "w", encoding="utf-8") as f:
        json.dump(dict1, f, indent=4)


def writecards(listofgamecard: List[GameCard]) -> None:
    listofdict:List[dict] = []
    for i in range(len(listofgamecard)):
        listofdict.append(listofgamecard[i].__dict__)
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


def readinfo() -> Tuple[dict[str, int], List[GameCard], List[GroupGame]]:
    with open(PATH_GROUP_KP, "r", encoding="utf-8") as f:
        gpkpdict = json.load(f)
    with open(PATH_CARDSLIST, "r", encoding="utf-8") as f:
        cardslist = json.load(f)
    with open(PATH_ONGAME, "r", encoding="utf-8") as f:
        ongamelistdict = json.load(f)
    ongamelist:List[GroupGame] = []
    for i in range(len(ongamelistdict)):
        ongamelistdict.append(GroupGame(
            groupid=ongamelistdict[i]["groupid"], kpid=ongamelist[i]["kpid"], cards=ongamelist[i]["cards"]))
    gamecardlist:List[GameCard] = []
    for i in range(len(ongamelistdict)):
        gamecardlist.append(GameCard(cardslist[i]))
    return gpkpdict, gamecardlist, ongamelist


def readskilldict() -> dict:
    with open(PATH_SKILLDICT, 'r', encoding="utf-8") as f:
        d = json.load(f)
    return d


def readjobdict() -> dict:
    with open(PATH_JOBDICT, 'r', encoding='utf-8') as f:
        d = json.load(f)
    return d
