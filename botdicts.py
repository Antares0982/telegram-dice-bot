# -*- coding:utf-8 -*-
import copy
import json
from typing import Tuple, List, Dict
from cfg import *
from gameclass import *


def writekpinfo(dict1: dict) -> None:
    with open(PATH_GROUP_KP, "w", encoding="utf-8") as f:
        json.dump(dict1, f, indent=4, ensure_ascii=False)


def writecards(listofgamecard: Dict[int, Dict[int, GameCard]]) -> None:
    listofdict: Dict[str, Dict[str, dict]] = {}
    for gpid in listofgamecard:
        if len(listofgamecard[gpid]) == 0:
            listofgamecard.pop(gpid)
            continue
        listofdict[str(gpid)] = {}
        for cdids in listofgamecard[gpid]:
            listofdict[str(gpid)][str(cdids)
                                   ] = listofgamecard[gpid][cdids].__dict__
    with open(PATH_CARDSLIST, "w", encoding="utf-8") as f:
        json.dump(listofdict, f, indent=4, ensure_ascii=False)


def writegameinfo(listofobj: List[GroupGame]) -> None:
    savelist: List[dict] = []
    for i in range(len(listofobj)):
        savelist.append(copy.deepcopy(listofobj[i].__dict__))
        savelist[-1]["gamerule"] = savelist[-1]["gamerule"].__dict__
        tpcards: List[GameCard] = savelist[-1]["cards"]
        savelist[-1]["cards"] = []
        savelist[-1].pop("kpcards")
        for i in tpcards:
            savelist[-1]["cards"].append(i.__dict__)
    with open(PATH_ONGAME, "w", encoding="utf-8") as f:
        json.dump(savelist, f, indent=4, ensure_ascii=False)


def readinfo() -> Tuple[Dict[int, int], Dict[int, Dict[int, GameCard]], List[GroupGame]]:
    # create file if not exist
    # group-kp
    try:
        f = open(PATH_GROUP_KP, "r", encoding="utf-8")
        f.close()
    except FileNotFoundError:
        with open(PATH_GROUP_KP, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        print("File does not exist, create new file")
        gpkpdict: Dict[int, int] = {}
    else:
        with open(PATH_GROUP_KP, "r", encoding="utf-8") as f:
            gpkpstrdict: Dict[str, int] = json.load(f)
        gpkpdict: Dict[int, int] = {}
        for keys in gpkpstrdict:
            gpkpdict[int(keys)] = gpkpstrdict[keys]
    print("kp info: passed")
    # cards
    try:
        f = open(PATH_CARDSLIST, "r", encoding="utf-8")
        f.close()
    except FileNotFoundError:
        with open(PATH_CARDSLIST, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        print("File does not exist, create new file")
        cardslist = {}
    else:
        with open(PATH_CARDSLIST, "r", encoding="utf-8") as f:
            cardslist = json.load(f)
    gamecardlist: Dict[int, dict] = {}
    for groupkeys in cardslist:
        gamecardlist[int(groupkeys)] = {}
        for keys in cardslist[groupkeys]:
            gamecardlist[int(groupkeys)][int(keys)] = GameCard(
                cardslist[groupkeys][keys])
    print("card info: passed")
    # games
    try:
        f = open(PATH_ONGAME, "r", encoding="utf-8")
        f.close()
    except FileNotFoundError:
        with open(PATH_ONGAME, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4, ensure_ascii=False)
        print("File does not exist, create new file")
        ongamelistdict = []
    else:
        with open(PATH_ONGAME, "r", encoding="utf-8") as f:
            ongamelistdict = json.load(f)
    ongamelist: List[GroupGame] = []
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


def readcurrentcarddict() -> dict:
    try:
        f = open(PATH_CURRENTCARDDICT, "r", encoding="utf-8")
        f.close()
    except FileNotFoundError:
        with open(PATH_CURRENTCARDDICT, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        d = {}
    else:
        with open(PATH_CURRENTCARDDICT, 'r', encoding='utf-8') as f:
            d = json.load(f)
    d1 = {}
    for keys in d:
        d1[int(keys)] = (d[keys][0], d[keys][1])
    return d1


def writecurrentcarddict(d: Dict[int, Tuple[int, int]]) -> None:
    with open(PATH_CURRENTCARDDICT, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=4, ensure_ascii=False)
