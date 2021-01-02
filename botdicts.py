# -*- coding:utf-8 -*-
import copy
import json
from typing import Tuple, List, Dict
from cfg import *
from gameclass import *


def writekpinfo(dict1: dict) -> None:
    with open(PATH_GROUP_KP, "w", encoding="utf-8") as f:
        json.dump(dict1, f, indent=4, ensure_ascii=False)


def writecards(listofgamecard: List[GameCard]) -> None:
    listofdict:List[dict] = []
    for i in range(len(listofgamecard)):
        listofdict.append(listofgamecard[i].__dict__)
    with open(PATH_CARDSLIST, "w", encoding="utf-8") as f:
        json.dump(listofdict, f, indent=4, ensure_ascii=False)


def writegameinfo(listofobj: List[GroupGame]) -> None:
    savelist:List[dict] = []
    for i in range(len(listofobj)):
        savelist.append(copy.deepcopy(listofobj[i].__dict__))
        tpcards:List[GameCard] = savelist[-1]["cards"]
        savelist[-1]["cards"] = []
        savelist[-1].pop("kpcards")
        for i in tpcards:
            savelist[-1]["cards"].append(i.__dict__)
    with open(PATH_ONGAME, "w", encoding="utf-8") as f:
        json.dump(savelist, f, indent=4, ensure_ascii=False)


def readinfo() -> Tuple[Dict[str, int], List[GameCard], List[GroupGame]]:
    with open(PATH_GROUP_KP, "r", encoding="utf-8") as f:
        gpkpdict = json.load(f)
    print("kp info: passed")
    with open(PATH_CARDSLIST, "r", encoding="utf-8") as f:
        cardslist = json.load(f)
    gamecardlist:List[GameCard] = []
    for i in range(len(cardslist)):
        gamecardlist.append(GameCard(cardslist[i]))
    print("card info: passed")
    with open(PATH_ONGAME, "r", encoding="utf-8") as f:
        ongamelistdict = json.load(f)
    ongamelist:List[GroupGame] = []
    for i in range(len(ongamelistdict)):
        ongamelist.append(GroupGame(ongamelistdict[i]))
    print("game info: passed")
    return gpkpdict, gamecardlist, ongamelist


def readskilldict() -> dict:
    with open(PATH_SKILLDICT, 'r', encoding="utf-8") as f:
        d = json.load(f)
    return d


def readjobdict() -> dict:
    with open(PATH_JOBDICT, 'r', encoding='utf-8') as f:
        d = json.load(f)
    return d
